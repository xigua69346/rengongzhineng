import numpy as np

class ThresholdDetector:
    def fit(self,z):
        self.center=np.median(z,axis=0)
        self.width=np.maximum(np.quantile(np.abs(z-self.center),0.99,axis=0,method='higher'),1e-6)
        return self
    def contributions(self,z): return np.abs(z-self.center)/self.width
    def score(self,z): return self.contributions(z).max(axis=1)
