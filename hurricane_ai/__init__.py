import os

# Base directory of project
PROJ_BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# Raw input data file constants
HURRICANE_SOURCE_FILE = os.path.join(PROJ_BASE_DIR, 'data/source/hurdat2.txt')
ERROR_SOURCE_FILE = os.path.join(PROJ_BASE_DIR, 'data/source/1970-present_OFCL_v_BCD5_ind_ATL_TI_errors_noTDs.txt')

# Processed data file constants
HURRICANE_PKL_FILE = os.path.join(PROJ_BASE_DIR, 'data/processed/hurricane_data.pkl')
HURRICANE_IDS_FILE = os.path.join(PROJ_BASE_DIR, 'data/processed/hurricane_ids.txt')
ERROR_PKL_FILE = os.path.join(PROJ_BASE_DIR, 'data/processed/error_data.pkl')
TRAIN_TEST_NPZ_FILE = os.path.join(PROJ_BASE_DIR, 'data/processed/train_test_data.npz')
SCALED_TRAIN_TEST_NPZ_FILE = os.path.join(PROJ_BASE_DIR, 'data/processed/scaled_train_test_data.npz')
SCALER_FILE = os.path.join(PROJ_BASE_DIR, 'scaler/feature_scaler.pkl')

# ML model constants
BD_LSTM_TD_MODEL = os.path.join(PROJ_BASE_DIR, 'models/bd_lstm_td.h5')
BD_LSTM_TD_MODEL_HIST = os.path.join(PROJ_BASE_DIR, 'models/bd_lstm_td_hist.csv')
LSTM_TD_MODEL = os.path.join(PROJ_BASE_DIR, 'models/lstm_td.h5')
LSTM_TD_MODEL_HIST = os.path.join(PROJ_BASE_DIR, 'models/lstm_td_hist.csv')


def is_source_modified(source_file, processed_file):
    """
    Determines whether the source file has been modified since the processed file was written.
    :param source_file: Source file.
    :param processed_file: Processed file.
    :return: Boolean indicator of whether the source has been modified.
    """
    return os.path.getmtime(source_file) > os.path.getmtime(processed_file)
