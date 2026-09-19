import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from typing import List
from src.ml.dataset import CLASSES

def evaluate_predictions(y_true: List[int], y_pred: List[int]) -> dict:
    """
    Generate comprehensive metrics for the test set.
    """
    labels_present = sorted(list(set(y_true).union(set(y_pred))))
    
    acc = accuracy_score(y_true, y_pred)
    p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels_present, average='macro', zero_division=0)
    p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels_present, average='weighted', zero_division=0)
    
    p_cls, r_cls, f1_cls, s_cls = precision_recall_fscore_support(y_true, y_pred, labels=list(range(len(CLASSES))), zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES))))
    
    per_class = {}
    for i, cls in enumerate(CLASSES):
        per_class[cls] = {
            "Precision": float(p_cls[i]),
            "Recall": float(r_cls[i]),
            "F1": float(f1_cls[i]),
            "Support": int(s_cls[i])
        }
        
    return {
        "Accuracy": float(acc),
        "Macro_Precision": float(p_mac),
        "Macro_Recall": float(r_mac),
        "Macro_F1": float(f1_mac),
        "Weighted_F1": float(f1_wt),
        "Per_Class": per_class,
        "Confusion_Matrix": cm.tolist()
    }
