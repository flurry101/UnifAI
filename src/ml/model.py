import os
import json
import lightgbm as lgb
import numpy as np
from typing import Dict, Any, Tuple
from src.ml.dataset import CLASSES

class Lane7Ranker:
    def __init__(self, model_params: Dict[str, Any] = None):
        # We define a basic configuration for multiclass
        self.params = model_params or {
            "objective": "multiclass",
            "num_class": len(CLASSES),
            "metric": "multi_logloss",
            "boosting_type": "gbdt",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "max_depth": 5,
            "verbose": -1,
            "random_state": 42
        }
        self.model = None
        self.features_schema = []
        
    def fit(self, X_train, y_train, X_val, y_val, feature_names):
        self.features_schema = feature_names
        
        train_data = lgb.Dataset(X_train, label=y_train, feature_name=feature_names)
        val_data = lgb.Dataset(X_val, label=y_val, feature_name=feature_names, reference=train_data)
        
        callbacks = [lgb.early_stopping(stopping_rounds=20)]
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=500,
            valid_sets=[train_data, val_data],
            callbacks=callbacks
        )
        
    def predict_proba(self, X):
        if self.model is None:
            raise ValueError("Model is not trained.")
        return self.model.predict(X)
        
    def predict(self, X):
        probs = self.predict_proba(X)
        # Returns index of highest probability
        return np.argmax(probs, axis=1)

    def feature_importance(self) -> Dict[str, float]:
        if self.model is None:
            return {}
        imp = self.model.feature_importance(importance_type="split")
        names = self.model.feature_name()
        return dict(zip(names, imp))

    def save(self, output_dir: str):
        if self.model is None:
            raise ValueError("Model not trained.")
        os.makedirs(output_dir, exist_ok=True)
        model_path = os.path.join(output_dir, "lgb_model.txt")
        meta_path = os.path.join(output_dir, "metadata.json")
        
        self.model.save_model(model_path)
        metadata = {
            "model": "LightGBM",
            "version": "1.0",
            "feature_schema": self.features_schema,
            "classes": CLASSES,
            "params": self.params
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=4)
            
    def load(self, input_dir: str):
        model_path = os.path.join(input_dir, "lgb_model.txt")
        meta_path = os.path.join(input_dir, "metadata.json")
        
        self.model = lgb.Booster(model_file=model_path)
        with open(meta_path, "r") as f:
            metadata = json.load(f)
        self.features_schema = metadata["feature_schema"]
        self.params = metadata["params"]
