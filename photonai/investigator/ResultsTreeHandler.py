import numpy as np
from photonai.validation.ResultsDatabase import MDBHelper
from photonai.photonlogger.Logger import Logger


class ResultsTreeHandler():
    def __init__(self, res_file):
        self.results = MDBHelper.load_results(res_file)

    def get_val_preds(self):
        y_true = []
        y_pred = []
        fold_idx = []
        for i, fold in enumerate(self.results.outer_folds):
            y_true.extend(fold.best_config.inner_folds[-1].validation.y_true)
            y_pred.extend(fold.best_config.inner_folds[-1].validation.y_pred)
            fold_idx.extend(np.repeat(i, len(fold.best_config.inner_folds[-1].validation.y_true)))
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        fold_idx = np.asarray(fold_idx)
        return {'y_true': y_true, 'y_pred': y_pred, 'fold_idx': fold_idx}

    def get_imps(self):
        imps = []
        fold_idx = []
        for i, fold in enumerate(self.results.outer_folds):
            imps.append(fold.best_config.inner_folds[-1].training.feature_importances)
            fold_idx.extend(np.repeat(i, len(fold.best_config.inner_folds[-1].training.y_true)))
        imps = np.asarray(imps)
        fold_idx = np.asarray(fold_idx)
        #return {'imps': imps, 'fold_idx': fold_idx}
        return imps

    def plot_confusion_matrix(self, classes=None, normalize=False, title='Confusion matrix'):
        """
        This function prints and plots the confusion matrix.
        Normalization can be applied by setting `normalize=True`.
        """
        import matplotlib.pyplot as plt
        import itertools
        from sklearn.metrics import confusion_matrix

        preds = ResultsTreeHandler.get_val_preds(self)
        cm = confusion_matrix(preds['y_true'], preds['y_pred'])
        np.set_printoptions(precision=2)
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            Logger().info("Normalized confusion matrix")
        else:
            Logger().info('Confusion matrix')
        Logger().info(cm)

        plt.figure()
        cmap = plt.cm.Blues
        plt.imshow(cm, interpolation='nearest', cmap=cmap)
        plt.title(title)
        plt.colorbar()

        if classes == None:
            classes = ['class ' + str(c + 1) for c in np.unique(preds['y_true'])]
        tick_marks = np.arange(len(classes))
        plt.xticks(tick_marks, classes, rotation=45)
        plt.yticks(tick_marks, classes)

        fmt = '.2f' if normalize else 'd'
        thresh = cm.max() / 2.
        for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
            plt.text(j, i, format(cm[i, j], fmt),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")

        plt.tight_layout()
        plt.ylabel('True label')
        plt.xlabel('Predicted label')
        plt.show()


