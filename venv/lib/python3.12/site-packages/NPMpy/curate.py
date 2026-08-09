# ====================
#  Necessary packages
# ====================

import os
import pandas as pd
from pandas import testing as tm

# ============================
#  Functions for loading data
# ============================

def curate_NPM(path):

    """
    Reads all .NPM.csv files from the input directory and saves
    a new .csv file each RegionXG in the files.

    Parameters
    ----------
    path : str
        directory containing subdirectory (ex. Rat1, Rat2, etc.) which contain .NPM.csv files

    Returns
    -------
    This function does not return variables, but instead saves the read data
    into new .csv files.
    """

    # get the immediate subdirectories of the input path
    sub_dirs = _get_immediate_subdirectories(path)

    # for each sub directory ...
    for sub in sub_dirs:
        sub_path = os.path.join(path, sub)
        NPM_415 = []
        NPM_470 = []
        NPM_560 = []

        # for each file in sub directory ...
        for file in os.listdir(sub_path):


            if (file.lower().endswith('.npm.csv')): # if directory, skip

                display(file)
                # read csv files
                data = pd.read_csv(os.path.join(sub_path, file))
                if 1 in data['LedState'].values: # if 1, 415
                    NPM_415 = data

                elif 2 in data['LedState'].values: # if 2, 470
                    NPM_470 = data

                elif 4 in data['LedState'].values: # if 4, 560
                    NPM_560 = data

        if type(NPM_415) == list: # if variable is list (i.e., no dataframe)
            continue

        else:

            if len(NPM_560) > 0:
                _curate_NPM_subdir(NPM_415, NPM_470, name=sub+'_470', save_path=sub_path)
                _curate_NPM_subdir(NPM_415, NPM_560, name=sub+'_560', save_path=sub_path)

            else:
                # curate and save NPM data
                _curate_NPM_subdir(NPM_415, NPM_470, name=sub, save_path=sub_path)
    return


def _curate_NPM_subdir(control, signal, name, save_path):

    """
    Helper function combining _curate_and_save_NPM() and _drop_preTTL() functions into one step.

    Parameters
    ----------
    control : dataframe
        dataframe containing the 415 data

    signal : dataframe
        dataframe containing the 470 or 560 data

    name : str
        subject name for the data, derived from the subdirectory folder names

    save_path : str
        directory where new .csv files will be saved. This is set to the sub directory by default.

    Returns
    -------
    This function does not return variables, but instead saves the read data
    into new .csv files.
    """

    if 1 not in control['LedState'].values:
        raise Exception('"1" not found in LedState column. Make sure that 415 and 470/560 are first and second input variables, respectively.')

    control_short = _drop_preTTL(control)
    signal_short = _drop_preTTL(signal)

    _curate_and_save_NPM(control_short, signal_short, name, save_path)
    return


# Get indexes of TTL (529 or 530 depending in 415 or 470)
#  then get the data from 1 row before first TTL trigger

def _drop_preTTL(NPM_df):

    """
    Helper function that finds the first TTL trigger and drops the data before it.

    Parameters
    ----------
    NPM_df : dataframe
        dataframe containing the either NPM data with Flags.

    Returns
    -------
    NPM_df_short : dataframe
        dataframe without the pre-TTL data and reset indexes.
    """

    TTL_idxs = NPM_df[NPM_df['Input0'] > 0]

    if len(TTL_idxs.index[:]) > 1:
        First_TTL = TTL_idxs.index[0]
        NPM_df_short = NPM_df.iloc[First_TTL-1:].reset_index()

    else:
        NPM_df_short = NPM_df

    return NPM_df_short


# Curate data and save as one new .csv file per region
def _curate_and_save_NPM(control_short, signal_short, name, save_path):

    """
    Helper function that takes shortened NPM (dropped preTTL) data and curates the data.
    In short, a new .csv file is created and saved for each RegionXG signal in 415 (Control)
    and 470 (Signal) files.

    Parameters
    ----------
    control_short : dataframe
        dataframe containing the control data that has dropped preTTL data

    signal_short : dataframe
        dataframe containing the signal that has dropped preTTL data

    name : str
        subject name for the data, derived from the subdirectory folder names

    save_path : str
        directory where new .csv files will be saved. This is set to the sub directory by default.

    Returns
    -------
    This function does not return variables, but instead saves the read data
    into new .csv file
    """

    regions_control = control_short.columns[8:]
    regions_signal = signal_short.columns[8:]
    tm.assert_index_equal(regions_control, regions_signal)

    for region in regions_control:

        data_control = control_short[region]
        data_signal = signal_short[region]

        region_dict = {'Timestamp': control_short['Timestamp'],
                   'Signal': data_signal,
                   'Control': data_control}

        region_df = pd.DataFrame(data=region_dict)
        region_df = region_df.dropna()

        save_name = name + '_curated_NPM_' + region +'.csv'
        region_df.to_csv(os.path.join(save_path, save_name), index=False)
    return

def _get_immediate_subdirectories(a_dir):

    """
    Helper function that find outputs all immediate subdirectories for a given path.

    Parameters
    ----------
    a_dir : str
        any directory

    Returns
    -------
    sub_dirs : list
        list of all immediate subdirectories
    """

    return [sub_dirs for sub_dirs in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, sub_dirs))]
