import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier

X = np.array([[0.0, 0.0], [1.0, 1.0], [0.0, 1.0], [1.0, 0.0]])
y = np.array([0, 1, 1, 0])
model = RandomForestClassifier(random_state=0)
model.fit(X, y)
explainer = shap.TreeExplainer(model)
raw = explainer.shap_values(X)
print('shap version', shap.__version__)
print(type(raw))
if isinstance(raw, list):
    print('list len', len(raw))
    for i, item in enumerate(raw):
        print(i, type(item), getattr(item, 'shape', None), np.asarray(item).shape)
else:
    arr = np.asarray(raw)
    print('ndarray shape', arr.shape, 'ndim', arr.ndim)
