from ..photonlogger.Logger import Logger
from sklearn.base import BaseEstimator
from skimage.util.shape import view_as_windows
from nilearn.image import resample_img, smooth_img
from nibabel.nifti1 import Nifti1Image
import numpy as np


# Smoothing
class SmoothImages(BaseEstimator):
    def __init__(self, fwhm=[2, 2, 2]):

        super(SmoothImages, self).__init__()

        # initialize private variable and
        self._fwhm = None
        self.fwhm = fwhm

    def fit(self, X, y=None, **kwargs):
        return self

    @property
    def fwhm(self):
        return self._fwhm

    @fwhm.setter
    def fwhm(self, fwhm):
        if isinstance(fwhm, int):
            self._fwhm = [fwhm, fwhm, fwhm]
        elif isinstance(fwhm, list):
            if len(fwhm) != 3:
                raise Exception("fwhm parameter should be either an integer (3) or a in the form of [3, 3, 3]")
            else:
                self._fwhm = fwhm

    def transform(self, X, y=None, **kwargs):
        smoothed_img = smooth_img(X, fwhm=self.fwhm)
        return smoothed_img


class ResampleImages(BaseEstimator):
    """
     Resampling voxel size
    """
    def __init__(self, voxel_size=[3, 3, 3]):
        self._voxel_size = None
        self.voxel_size = voxel_size

    def fit(self, X, y=None, **kwargs):
        return self

    @property
    def voxel_size(self):
        return self._voxel_size

    @voxel_size.setter
    def voxel_size(self, voxel_size):
        if isinstance(voxel_size, int):
            self._voxel_size = [voxel_size, voxel_size, voxel_size]
        elif isinstance(voxel_size, list):
            if len(voxel_size) != 3:
                raise Exception("voxel_size parameter should be either an integer (3) or a in the form of [3, 3, 3]")
            else:
                self._voxel_size = voxel_size

    def transform(self, X, y=None, **kwargs):
        target_affine = np.diag(self.voxel_size)

        if isinstance(X, list) and len(X) == 1:
            resampled_img = resample_img(X[0], target_affine=target_affine, interpolation='nearest')
        else:
            resampled_img = resample_img(X, target_affine=target_affine, interpolation='nearest')
            resampled_img = np.moveaxis(resampled_img.dataobj, -1, 0)
        if not isinstance(resampled_img, list) and not isinstance(resampled_img, np.ndarray):
            resampled_img = np.array([resampled_img])
        return resampled_img


class PatchImages(BaseEstimator):

    def __init__(self, patch_size=25, random_state=42, nr_of_processes=3):
        Logger().info("Nr or processes: " + str(nr_of_processes))
        super(PatchImages, self).__init__(output_img=True, nr_of_processes=nr_of_processes)
        # Todo: give cache folder to mother class

        self.patch_size = patch_size
        self.random_state = random_state

    def fit(self, X, y=None, **kwargs):
        return self

    def transform(self, X, y=None, **kwargs):
        Logger().info("Drawing patches")
        return self.draw_patches(X, self.patch_size)


    @staticmethod
    def draw_patches(patch_x, patch_size):
        if not isinstance(patch_x, list):
            return PatchImages.draw_patch_from_mri(patch_x, patch_size)
        else:
            return_list = []
            for p in patch_x:
                print(str(p))
                return_list.append(PatchImages.draw_patch_from_mri(p, patch_size))
            return return_list

    @staticmethod
    def draw_patch_from_mri(patch_x, patch_size):
        # Logger().info("drawing patch..")
        if isinstance(patch_x, str):
            from nilearn import image
            patch_x = np.ascontiguousarray(image.load_img(patch_x).get_data())

        if isinstance(patch_x, Nifti1Image):
            patch_x = np.ascontiguousarray(patch_x.dataobj)

        patches_drawn = view_as_windows(patch_x, (patch_size, patch_size, 1), step=1)

        patch_list_length = patches_drawn.shape[0]
        patch_list_width = patches_drawn.shape[1]

        output_matrix = patches_drawn[0:patch_list_length:patch_size, 0:patch_list_width:patch_size, :, :]

        # TODO: Reshape First 3 Matrix Dimensions into 1, which will give 900 images
        output_matrix = output_matrix.reshape((-1, output_matrix.shape[3], output_matrix.shape[4], output_matrix.shape[5]))
        output_matrix = np.squeeze(output_matrix)

        return output_matrix

    def copy_me(self):
        return PatchImages(self.patch_size, self.random_state, self.nr_of_processes)

    def _draw_single_patch(self):
        pass
