import numpy as np
import os.path
import inspect
import glob
from nilearn.input_data import NiftiMasker
from nilearn import image
import nibabel as nib
import time
from pathlib import Path
from sklearn.base import BaseEstimator

from ..photonlogger.Logger import Logger, Singleton


class RoiObject:

    def __init__(self, index=0, label='', size=0, mask=None):
        self.index = index
        self.label = label
        self.size = size
        self.mask = None
        self.is_empty = False


class AtlasObject:

    def __init__(self, name='', path='', labels_file='', mask_threshold=None):
        self.name = name
        self.path = path
        self.labels_file = labels_file
        self.mask_threshold = mask_threshold
        self.indices = list()
        self.roi_list = list()
        self.map = None


@Singleton
class AtlasLibrary:

    def __init__(self):

        # Get which atlases are available in Atlases subdir of this module
        # all have to be in *.(nii/img).gz! (Could be nicer)
        self.atlas_dir = os.path.dirname(inspect.getfile(BrainAtlas)) + '/' + 'Atlases/'
        self.available_atlasses = None
        self.loaded_atlasses = None

    def _inspect_atlas_dir(self):

        atlas_files = glob.glob(self.atlas_dir + '*/*.nii.gz')
        for atlas_file in atlas_files:
            atlas_id = os.path.basename(atlas_file)[:-7]
            if self.available_atlasses is None:
                self.available_atlasses = dict()
            self.available_atlasses[atlas_id] = AtlasObject(name=atlas_id,
                                                            path=atlas_file,
                                                            labels_file=atlas_file[:-7] + '_labels.txt')

    def _load_atlas(self, atlas_name, target_affine=None, target_shape=None, mask_threshold=None):

        print("Loading Atlas")
        # load atlas object and copy it
        atlas_obj_orig = self.available_atlasses[atlas_name]
        atlas_obj = AtlasObject(atlas_obj_orig.name, atlas_obj_orig.path,
                                atlas_obj_orig.labels_file,
                                atlas_obj_orig.mask_threshold)
        atlas_obj.map = atlas_obj_orig.map
        atlas_obj.indices = atlas_obj_orig.indices
        atlas_obj.map = image.load_img(atlas_obj.path).get_data()

        # load it and adapt it to target affine and target shape
        if mask_threshold is not None:
            atlas_obj.map = atlas_obj.map > self.mask_threshold  # get actual map data with probability maps
            atlas_obj.map = atlas_obj.map.astype(int)

        atlas_obj.indices = list(np.unique(atlas_obj.map))

        # check labels
        if Path(atlas_obj.labels_file).is_file():  # if we have a file with indices and labels
            # Logger().info('Using labels from file (' + str(atlas_obj.labels_file) + ')')
            labels_dict = dict()

            with open(atlas_obj.labels_file) as f:
                for line in f:
                    (key, val) = line.split("\t")
                    labels_dict[int(key)] = val

            # check if map indices correspond with indices in the labels file
            if not sorted(atlas_obj.indices) == sorted(list(labels_dict.keys())):
                Logger().info(
                    'The indices in map image ARE NOT the same as those in your *_labels.txt! Ignoring *_labels.txt.')
                Logger().info('MapImage: ')
                Logger().info(sorted(self.indices))
                Logger().info('File: ')
                Logger().info(sorted(list(labels_dict.keys())))

                atlas_obj.roi_list = [RoiObject(index=i, label=str(i), size=np.sum(i == atlas_obj.map)) for i in atlas_obj.indices]
            else:
                for i in range(len(atlas_obj.indices)):
                    roi_index = atlas_obj.indices[i]
                    new_roi = RoiObject(index=roi_index, label=labels_dict[roi_index].replace('\n', ''),
                                        size=np.sum(roi_index == atlas_obj.map))
                    atlas_obj.roi_list.append(new_roi)

        else:  # if we don't have a labels file, we just use str(indices) as labels
            atlas_obj.roi_list = [RoiObject(index=i, label=str(i), size=np.sum(i == atlas_obj.map)) for i in
                                  atlas_obj.indices]

        # check for empty ROIs and extract roi mask
        for roi in atlas_obj.roi_list:

            if roi.size == 0:
                continue
                # Logger().info('ROI with index ' + str(roi.index) + ' and label ' + roi.label + ' does not exist!')

            roi.mask = image.new_img_like(atlas_obj.path, atlas_obj.map == roi.index)
            if target_affine is not None and target_shape is not None:
                roi.mask = image.resample_img(roi.mask, target_affine=target_affine, target_shape=target_shape,
                                              interpolation='nearest')

                # check orientations
                orient_data = ''.join(nib.aff2axcodes(target_affine))
                orient_roi = ''.join(nib.aff2axcodes(roi.mask.affine))
                orient_ok = orient_roi == orient_data
                if not orient_ok:
                    pass
                    # Logger().info('Orientation of mask and data are not the same: '
                    #               + orient_roi + ' (mask) vs. ' + orient_data + ' (data)')

            # check if roi is empty
            if np.sum(roi.mask.dataobj != 0) == 0:
                # Logger().info('No voxels in ROI after resampling (' + roi.label + ').')
                roi.is_empty = True

        if self.loaded_atlasses is None:
            self.loaded_atlasses = dict()
        self.loaded_atlasses[(atlas_name, str(target_affine), str(target_shape))] = atlas_obj
        print("Loading Atlas done!")

    def get_atlas(self, atlas_name, target_affine=None, target_shape=None, mask_threshold=None):

        if self.available_atlasses is None:
            self._inspect_atlas_dir()

        if self.loaded_atlasses is None or (atlas_name, str(target_affine), str(target_shape)) not in self.loaded_atlasses:
            print("Loading Atlas from filesystem")
            self._load_atlas(atlas_name, target_affine, target_shape, mask_threshold)

        return self.loaded_atlasses[(atlas_name, str(target_affine), str(target_shape))]

    @staticmethod
    def find_rois_by_label(atlas_obj, query_list):
        return [i for i in atlas_obj.roi_list if i.label in query_list]

    @staticmethod
    def find_rois_by_index(atlas_obj, query_list):
        return [i for i in atlas_obj.roi_list if i.index in query_list]

    @staticmethod
    def get_nii_files_from_folder(folder_path, extension=".nii.gz"):
        return glob.glob(folder_path + '*' + extension)


class BrainAtlas(BaseEstimator):
    def __init__(self, atlas_name: str, extract_mode: str='vec',
                 mask_threshold=None, background_id=0, rois='all'):

        # ToDo
        # + add-own-atlas capability
        # + get atlas infos (.getInfo('AAL'))
        # + ROIs by name (e.g. in HarvardOxford subcortical: ['Caudate_L', 'Caudate_R'])
        # + get ROIs by map indices (e.g. in AAL: [2001, 2111])
        # + finish mask-img matching
        #   + reorientation/affine transform
        #   + voxel-size (now returns true number of voxels (i.e. after resampling) vs. voxels in mask)
        #   + check RAS vs. LPS view-type and provide warning
        # + handle "disappearing" ROIs when downsampling in map check
        # - pretty getBox function (@Claas)
        # + prettify box-output (to 4d np array)
        # - unit tests
        # Later
        # - add support for overlapping ROIs and probabilistic atlases using 4d-nii
        # - add support for 4d resting-state data using nilearn

        self.atlas_name = atlas_name
        self.extract_mode = extract_mode
        # collection mode default to concat --> can only be overwritten by AtlasMapper
        self.collection_mode = 'concat'
        self.mask_threshold = mask_threshold
        self.background_id = background_id
        self.rois = rois
        self.box_shape = []
        self.is_transformer = True

    def fit(self, X, y):
        return self

    def transform(self, X, y=None, **kwargs):

        if len(X) < 1:
            raise Exception("Brain Atlas: Did not get any data in parameter X")

        if self.collection_mode == 'list' or self.collection_mode == 'concat':
            collection_mode = self.collection_mode
        else:
            collection_mode = 'concat'
            Logger().error("Collection mode {} not supported. Use 'list' or 'concat' instead."
                           "Falling back to concat mode.".format(self.collection_mode))

        # 1. validate if all X are in the same space and have the same voxelsize and have the same orientation

        # 2. load sample data to get target affine and target shape to adapt the brain atlas

        affine, shape = BrainMasker.get_format_info_from_first_image(X)

        # load all niftis to memory
        if isinstance(X, list):
            n_subjects = len(X)
            X = image.load_img(X)
        elif isinstance(X, str):
            n_subjects = 1
            X = image.load_img(X)
        else:
            n_subjects = X.shape[-1]

        # get ROI mask
        atlas_obj = AtlasLibrary().get_atlas(self.atlas_name, affine, shape, self.mask_threshold)
        roi_objects = self._get_rois(atlas_obj, which_rois=self.rois, background_id=self.background_id)

        roi_data = [list() for i in range(n_subjects)]
        roi_data_concat = list()
        t1 = time.time()
        for roi in roi_objects:
            Logger().debug("Extracting ROI {}".format(roi.label))
            masker = BrainMasker(mask_image=roi, affine=affine, shape=shape, extract_mode=self.extract_mode)
            extraction = masker.transform(X)

            if collection_mode == 'list':
                for sub_i in range(extraction.shape[0]):
                    roi_data[sub_i].append(extraction[sub_i])
            else:
                roi_data_concat.append(extraction)

        if self.collection_mode == 'concat':
            roi_data = np.concatenate(roi_data_concat, axis=1)

        elapsed_time = time.time() - t1
        Logger().debug("Time for extracting {} ROIs in {} subjects: {} seconds".format(len(roi_objects), n_subjects, elapsed_time))
        return roi_data

    @staticmethod
    def _get_rois(atlas_obj, which_rois='all', background_id=0):

        if isinstance(which_rois, str):
            if which_rois == 'all':
                return [roi for roi in atlas_obj.roi_list if roi.index != background_id]
            else:
                return AtlasLibrary().find_rois_by_label(atlas_obj, [which_rois])

        elif isinstance(which_rois, int):
            return AtlasLibrary().find_rois_by_index(atlas_obj, [which_rois])

        elif isinstance(which_rois, list):
            if isinstance(which_rois[0], str):
                if which_rois[0].lower() == 'all':
                    return AtlasLibrary().find_rois_by_label(atlas_obj, which_rois[0])
                else:
                    return AtlasLibrary().find_rois_by_label(atlas_obj, which_rois)
            else:
                return AtlasLibrary().find_rois_by_index(atlas_obj, which_rois)


class BrainMasker(BaseEstimator):

    def __init__(self, mask_image=None, affine=None, shape=None, extract_mode='vec'):
        self.mask_image = mask_image
        self.affine = affine
        self.shape = shape
        self.masker = None
        self.extract_mode = extract_mode

    @staticmethod
    def get_format_info_from_first_image(X):
        if isinstance(X, str):
            img = image.load_img(X)
        elif isinstance(X[0], str):
            img = image.load_img(X[0])
        elif isinstance(X[0], nib.Nifti1Image):
            img = X[0]
        else:
            error_msg = "Can only process strings as file paths to nifti images or nifti image object"
            Logger().error(error_msg)
            raise ValueError(error_msg)

        if len(img.shape) > 3:
            img_shape = img.shape[:3]
        else:
            img_shape = img.shape
        return img.affine, img_shape

    @staticmethod
    def _get_box(in_imgs, roi):
        # get ROI infos
        map = roi.get_data()
        true_points = np.argwhere(map)
        corner1 = true_points.min(axis=0)
        corner2 = true_points.max(axis=0)
        box = []
        for img in in_imgs:
            if isinstance(img, str):
                data = image.load_img(img).get_data()
            else:
                data = img.get_data()
            tmp = data[corner1[0]:corner2[0] + 1, corner1[1]:corner2[1] + 1, corner1[2]:corner2[2] + 1]
            box.append(tmp)
        return np.asarray(box)

    def transform(self, X, y=None, **kwargs):

        if self.affine is None or self.shape is None:
            self.affine, self.shape = BrainMasker.get_format_info_from_first_image(X)

        if not self.mask_image.is_empty:
            self.masker = NiftiMasker(mask_img=self.mask_image.mask, target_affine=self.affine,
                                      target_shape=self.shape, dtype='float32')

            try:
                single_roi = self.masker.fit_transform(X)
            except BaseException as e:
                print(e)
                single_roi = None

            if single_roi is not None:
                if self.extract_mode == 'vec':
                    return np.asarray(single_roi)

                elif self.extract_mode == 'mean':
                    return np.mean(single_roi, axis=1)

                elif self.extract_mode == 'box':
                    return BrainMasker._get_box(X, self.mask_image)

                elif self.extract_mode == 'img':
                    return self.masker.inverse_transform(single_roi)

                else:
                    Logger().error("Currently there are no other methods than 'vec', 'mean', and 'box' supported!")
            else:
                print("Extracting ROI failed.")
        else:
            print("Skipping self.mask_image " + self.mask_image.label + " because it is empty.")


