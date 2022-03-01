import numpy as np
from sklearn import decomposition

def principal_component_analysis(cube_data, p_keep=1.0, n_components=0):

    cube_rows, cube_cols, cube_bands = cube_data.shape

    # if n_components undefined, use number of input features
    if n_components < 1:
        n_components = cube_bands

    source_data = np.reshape(cube_data, (cube_data.shape[0] * cube_data.shape[1], cube_data.shape[2]))
    n_samples, n_features = source_data.shape

    ### extract the data that should actually used for the fitting
    fitting_data = source_data
    if p_keep < 1.0:
        idx = np.arange(n_samples)
        np.random.shuffle(idx)
        idx = idx[:int(n_samples * p_keep)]
        fitting_data = fitting_data[idx, :]

    ### do the fitting
    pca = decomposition.PCA(n_components=n_components, svd_solver='full', whiten=True)
    pca.fit(fitting_data)

    result_data = pca.transform(source_data)
    result_data = np.reshape(result_data, (cube_rows, cube_cols, n_components))

    return result_data
