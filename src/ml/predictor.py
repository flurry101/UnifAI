from typing import Dict, Any
import numpy as np
from src.matching.models import PairFeatureResult
from src.ml.features import extract_features, get_feature_names
from src.ml.model import Lane7Ranker
from src.ml.dataset import CLASSES

class Lane7Predictor:
    def __init__(self, model_dir: str):
        self.ranker = Lane7Ranker()
        self.ranker.load(model_dir)
        self.feature_names = get_feature_names()
        
    def predict_relationship(self, result: PairFeatureResult) -> Dict[str, Any]:
        """
        Predict relationship and enforce Technical Conflict Safety Layer.
        """
        # 1. Feature extraction
        feats_dict = extract_features(result)
        
        # Ensure ordered correctly for LightGBM
        x_array = np.array([feats_dict[f] for f in self.feature_names]).reshape(1, -1)
        
        # 2. ML Prediction
        probs = self.ranker.predict_proba(x_array)[0]
        pred_idx = np.argmax(probs)
        raw_prediction = CLASSES[pred_idx]
        
        confidence = float(probs[pred_idx])
        prob_dict = {CLASSES[i]: float(probs[i]) for i in range(len(CLASSES))}
        
        # 3. Technical Conflict Safety Layer
        final_prediction = raw_prediction
        safety_triggered = False
        
        # Rule: A hard technical conflict CANNOT be overridden by ML to be IDENTICAL or EQUIVALENT.
        # It must be suppressed.
        if result.technical_conflict and raw_prediction in ["IDENTICAL", "EQUIVALENT"]:
            safety_triggered = True
            
            # Decide fallback based on the nature of conflict or evidence
            # We map unsafe predictions to DISTINCT (or UNDETERMINED if lack of evidence)
            # Typically a known technical conflict means DISTINCT.
            final_prediction = "DISTINCT"
            
        # Additional safety: If critical information is missing, and it predicts IDENTICAL, we may want to review it.
        # But we rely on ML to output UNDETERMINED. If ML is overconfident, safety layer could intervene.
        # For now, stick to the hard conflict rule requested.
        
        return {
            "ml_prediction": raw_prediction,
            "final_relationship": final_prediction,
            "probabilities": prob_dict,
            "confidence": confidence,
            "safety_rule_triggered": safety_triggered
        }
