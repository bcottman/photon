import warnings

import numpy as np
from nilearn.datasets import fetch_oasis_vbm
from sklearn.model_selection import ShuffleSplit

from photonai.base import Hyperpipe, PipelineElement, OutputSettings, Stack
from photonai.neuro import NeuroBranch
from photonai.neuro.brain_atlas import AtlasLibrary

warnings.filterwarnings("ignore", category=DeprecationWarning)


# GET DATA FROM OASIS
n_subjects = 50
dataset_files = fetch_oasis_vbm(n_subjects=n_subjects)
age = dataset_files.ext_vars['age'].astype(float)
y = np.array(age)
X = np.array(dataset_files.gray_matter_maps)


# DEFINE OUTPUT SETTINGS
settings = OutputSettings(project_folder='.')

# DESIGN YOUR PIPELINE
pipe = Hyperpipe('Limbic_System',
                 optimizer='grid_search',
                 metrics=['mean_absolute_error'],
                 best_config_metric='mean_absolute_error',
                 outer_cv=ShuffleSplit(n_splits=1, test_size=0.2),
                 inner_cv=ShuffleSplit(n_splits=1, test_size=0.2),
                 verbosity=2,
                 cache_folder="./cache",
                 eval_final_performance=False,
                 output_settings=settings)

"""
AVAILABLE ATLASES
    'AAL'
    'HarvardOxford_Cortical_Threshold_25'
    'HarvardOxford_Subcortical_Threshold_25'
    'HarvardOxford_Cortical_Threshold_50'
    'HarvardOxford_Subcortical_Threshold_50'
    'Yeo_7'
    'Yeo_7_Liberal'
    'Yeo_17'
    'Yeo_17_Liberal'
"""
# to list all roi names of a specific atlas, you can do the following
AtlasLibrary().list_rois('AAL')
AtlasLibrary().list_rois('HarvardOxford_Cortical_Threshold_25')
AtlasLibrary().list_rois('HarvardOxford_Subcortical_Threshold_25')

# PICK AN ATLAS
atlas = PipelineElement('BrainAtlas',
                        rois=['Hippocampus_L', 'Hippocampus_R', 'Amygdala_L', 'Amygdala_R'],
                        atlas_name="AAL", extract_mode='vec', batch_size=20)

# EITHER ADD A NEURO BRANCH OR THE ATLAS ITSELF
neuro_branch = NeuroBranch('NeuroBranch', nr_of_processes=2)
neuro_branch += atlas

# it's also possible to combine ROIs from different atlases
neuro_stack = Stack('HarvardOxford')

ho_sub = NeuroBranch('HO_Subcortical')
ho_sub += PipelineElement('BrainAtlas',
                          rois=['Left Thalamus', 'Left Caudate', 'Left Putamen', 'Left Pallidum'],
                          atlas_name="HarvardOxford_Subcortical_Threshold_25", extract_mode='vec', batch_size=20)

ho_cort = NeuroBranch('HO_Cortical')
ho_cort += PipelineElement('BrainAtlas',
                           rois=['Insular Cortex', 'Superior Frontal Gyrus', 'Middle Frontal Gyrus'],
                           atlas_name="HarvardOxford_Cortical_Threshold_25", extract_mode='vec', batch_size=20)

neuro_stack += ho_cort
neuro_stack += ho_sub

# ADD NEURO ELEMENTS TO HYPERPIPE

pipe += neuro_branch
#pipe += atlas
#pipe += neuro_stack

pipe += PipelineElement('PCA', n_components=20)

pipe += PipelineElement('RandomForestRegressor')

pipe.fit(X, y)
