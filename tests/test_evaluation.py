import numpy as np
from causalverse.detection.evaluation import metrics,delay

def test_confusion_metrics_and_missing_detection():
    m=metrics([0,0,1,1],[0,1,0,1]);assert m['Accuracy']==.5 and m['Macro_F1']==.5
    assert m['False_Positive_Rate']==.5
    assert delay(np.array([0,180,360]),[1,0,1],180)==180
    assert delay(np.array([0,180,360]),[1,0,0],180) is None
