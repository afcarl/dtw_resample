import numpy
from sklearn.base import BaseEstimator, TransformerMixin

from scipy.interpolate import interp1d

__author__ = 'Romain Tavenard romain.tavenard[at]univ-rennes2.fr'


class DTWSampler(BaseEstimator, TransformerMixin):
    saved_dtw_path = []
    
    def __init__(self, scaling_col_idx=0, reference_idx=0, d=1, n_samples=100,interp_kind="slinear",save_path=False):
        self.scaling_col_idx = scaling_col_idx
        self.reference_idx = reference_idx
        self.n_samples = n_samples
        self.d = d
        self.interp_kind = interp_kind
        self.reference_series = None
        
        # if saving dtw_Path
        self.save_path = save_path
        
    def fit(self, X):
        _X = X.reshape((X.shape[0], -1, self.d))
        end = last_index(_X[self.reference_idx])
        self.reference_series = resampled(_X[self.reference_idx, :end, self.scaling_col_idx], n_samples=self.n_samples,
                                          kind=self.interp_kind)
        return self

    def transform_3d(self, X):
        X_resampled = numpy.zeros((X.shape[0], self.n_samples, X.shape[2]))
        xnew = numpy.linspace(0, 1, self.n_samples)
        for i in range(X.shape[0]):
            end = last_index(X[i])
            for j in range(X.shape[2]):
                X_resampled[i, :, j] = resampled(X[i, :end, j], n_samples=self.n_samples, kind=self.interp_kind)
            # Compute indices based on alignment of dimension self.scaling_col_idx with the reference
            indices_xy = [[] for _ in range(self.n_samples)]
            
            if self.save_path and len(DTWSampler.saved_dtw_path)==(self.d+1): # verify if full dtw path already exists
                current_path = DTWSampler.saved_dtw_path[i]
            else:
                # append path
                current_path = dtw_path(X_resampled[i, :, self.scaling_col_idx], self.reference_series)           
                if self.save_path: # save current path is asked
                    DTWSampler.saved_dtw_path.append(current_path)                

            for t_current, t_ref in current_path:
                indices_xy[t_ref].append(t_current)
            for j in range(X.shape[2]):
                if False and j == self.scaling_col_idx:
                    X_resampled[i, :, j] = xnew
                else:
                    ynew = numpy.array([numpy.mean(X_resampled[i, indices, j]) for indices in indices_xy])
                    X_resampled[i, :, j] = ynew
        return X_resampled

    def transform(self, X):
        _X = X.reshape((X.shape[0], -1, self.d))
        return self.transform_3d(_X).reshape((X.shape[0], -1))

    def dump(self, fname):
        numpy.savetxt(fname, self.reference_series)


def resampled(X, n_samples=100, kind="linear"):
    xnew = numpy.linspace(0, 1, n_samples)
    f = interp1d(numpy.linspace(0, 1, X.shape[0]), X, kind=kind)
    return f(xnew)


def last_index(X):
    timestamps_infinite = numpy.all(~numpy.isfinite(X), axis=1)  # Are there NaNs padded after the TS?
    if numpy.alltrue(~timestamps_infinite):
        idx = X.shape[0]
    else:  # Yes? then remove them
        idx = numpy.nonzero(timestamps_infinite)[0][0]
    return idx


def empty_mask(s1, s2):
    l1 = s1.shape[0]
    l2 = s2.shape[0]
    mask = numpy.zeros((l1 + 1, l2 + 1))
    mask[1:, 0] = numpy.inf
    mask[0, 1:] = numpy.inf
    return mask


def dtw_path(s1, s2):
    l1 = s1.shape[0]
    l2 = s2.shape[0]

    cum_sum = numpy.zeros((l1 + 1, l2 + 1))
    cum_sum[1:, 0] = numpy.inf
    cum_sum[0, 1:] = numpy.inf
    predecessors = [([None] * l2) for i in range(l1)]

    for i in range(l1):
        for j in range(l2):
            if numpy.isfinite(cum_sum[i + 1, j + 1]):
                dij = numpy.linalg.norm(s1[i] - s2[j]) ** 2
                pred_list = [cum_sum[i, j + 1], cum_sum[i + 1, j], cum_sum[i, j]]
                argmin_pred = numpy.argmin(pred_list)
                cum_sum[i + 1, j + 1] = pred_list[argmin_pred] + dij
                if i + j > 0:
                    if argmin_pred == 0:
                        predecessors[i][j] = (i - 1, j)
                    elif argmin_pred == 1:
                        predecessors[i][j] = (i, j - 1)
                    else:
                        predecessors[i][j] = (i - 1, j - 1)

    i = l1 - 1
    j = l2 - 1
    best_path = [(i, j)]
    while predecessors[i][j] is not None:
        i, j = predecessors[i][j]
        best_path.insert(0, (i, j))
        
    return best_path
    
    
if __name__=='__main__':
    npy_arr = numpy.load('data/sample.npy')
    import time
    t0 = time.time()
    for i in range(1000):
        s = DTWSampler(scaling_col_idx=0, reference_idx=0, d=1,n_samples=20,save_path=True)
        transformed_array = s.fit_transform(npy_arr)
    print(time.time()-t0)