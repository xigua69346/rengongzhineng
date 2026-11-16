import numpy as np

class PCADetector:
    def fit(self,z,variance=0.90):
        self.center=z.mean(axis=0)
        _,singular,vt=np.linalg.svd(z-self.center,full_matrices=False)
        self.explained_variance=singular**2/(len(z)-1)
        self.ratio=self.explained_variance/self.explained_variance.sum()
        k=int(np.searchsorted(np.cumsum(self.ratio),variance)+1)
        self.components=vt[:k]; self.eigenvalues=np.maximum(self.explained_variance[:k],1e-12)
        return self
    def scores(self,z):
        centered=z-self.center; projection=centered@self.components.T
        residual=centered-projection@self.components
        t2=np.sum(projection**2/self.eigenvalues,axis=1)
        spe=np.sum(residual**2,axis=1)
        # Nonnegative orthogonal back-projection contributions sum to T2.
        t2_contribution=((projection/np.sqrt(self.eigenvalues))@self.components)**2
        return dict(T2=t2,SPE=spe,projection=projection,T2_contribution=t2_contribution,SPE_contribution=residual**2)
