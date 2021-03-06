from sklearn.datasets import load_boston
from sklearn.model_selection import KFold

from photonai.base import Hyperpipe, PipelineElement, OutputSettings
from photonai.optimization import IntegerRange
from photonai.investigator import Investigator


# Investigator.load_from_file("basic_svm_pipe_no_performance", "/home/rleenings/Git/photon_core/photonai/examples/basic/tmp/basic_svm_pipe_no_performance_results_2019-11-07_15-00-34/photon_result_file.p")

# WE USE THE BREAST CANCER SET FROM SKLEARN
X, y = load_boston(True)

# DESIGN YOUR PIPELINE
my_pipe = Hyperpipe(
    "basic_svm_pipe_no_performance",
    optimizer="random_grid_search",
    metrics=[
        "mean_squared_error",
        "pearson_correlation",
        "mean_absolute_error",
        "explained_variance",
    ],
    best_config_metric="mean_squared_error",
    outer_cv=KFold(n_splits=3),
    inner_cv=KFold(n_splits=3),
    verbosity=1,
    output_settings=OutputSettings(project_folder="./tmp/"),
    eval_final_performance=False,
)

# ADD ELEMENTS TO YOUR PIPELINE
# first normalize all features
my_pipe += PipelineElement("StandardScaler")

my_pipe += PipelineElement("PCA", hyperparameters={"n_components": [0.5, 0.8, 0.3]})

# engage and optimize the good old SVM for Classification
my_pipe += PipelineElement(
    "RandomForestRegressor", hyperparameters={"n_estimators": IntegerRange(10, 50)}
)


# NOW TRAIN YOUR PIPELINE
my_pipe.fit(X, y)

# AND SHOW THE RESULTS IN THE WEBBASED PHOTON INVESTIGATOR TOOL
Investigator.show(my_pipe)
