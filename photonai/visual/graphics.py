# !/usr/bin/env python
# -*- coding: utf-8 -*-
__coverage__ = 0.86
__author__ = "Bruce_H_Cottman"
__license__ = "MIT License" ""
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix
import seaborn as sn
import pandas as pd

def plot_cm(y,y_pred, cm = "Accent"):
    fig = plt.figure(figsize=(5*10/7,5))
    data = confusion_matrix(y, y_pred)
    df_cm = pd.DataFrame(data, columns=np.unique(y), index = np.unique(y))
    df_cm.index.name = 'Actual'
    df_cm.columns.name = 'Predicted'
    sn.set(font_scale=1.0)#for label size
    sn.heatmap(df_cm, cmap=cm, annot=True,annot_kws={"size": 16})# font size