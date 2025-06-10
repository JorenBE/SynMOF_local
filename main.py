import os
import sys

from settings import *

import pandas as pd
from datetime import datetime

from pymatgen.io.cif import CifParser
from molSimplify.Informatics.MOF.MOF_descriptors import get_MOF_descriptors

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import MOF_prediction_models

class CifFile():
    def __init__(self, file):
        if not os.path.exists(file):
            print(f'{file} does not exists.')
            return None
        
        self.file = file
        self.ciffile_name = os.path.basename(file)
        self.name = os.path.splitext(self.ciffile_name)[0]

        self.primitive_cif = None
        self.molsimplify_folder = None
        self.xyz_folder = None
    
    def _create_molsimplifyFolder(self, base_folder):
        molsim_folder = os.path.join(base_folder, 'molsimplify')
        if not os.path.exists(molsim_folder):
            os.mkdir(molsim_folder)
        self.molsimplify_folder = molsim_folder
    
    def _create_xyzFolder(self, base_folder):
        xyz_folder = os.path.join(base_folder, 'xyz')
        if not os.path.exists(xyz_folder):
            os.mkdir(xyz_folder)
        self.xyz_folder = xyz_folder

    def save_primitive(self, base_folder):
        s = CifParser(self.file, occupancy_tolerance=1).get_structures()[0]
        sprim = s.get_primitive_structure()
        
        saving_file = f'{base_folder}/mof_primitive.cif'
        sprim.to(filename = saving_file )
        print(f'Primitive cell saved in {saving_file}')
        self.primitive_cif = saving_file
    
    def get_descriptors(self, base_folder):
        if self.primitive_cif is None:
            self.save_primitive(base_folder)

        if self.molsimplify_folder is None:
            self._create_molsimplifyFolder(base_folder)

        if self.xyz_folder is None:
            self._create_xyzFolder(base_folder)

        full_names, full_descriptors = get_MOF_descriptors(self.primitive_cif,
                                                            3,
                                                            path = self.molsimplify_folder,
                                                            xyzpath= f"{self.xyz_folder}/mof.xyz")
        featurization_list = []

        full_names.append('filename')
        full_descriptors.append(self.file)
        featurization = dict(zip(full_names, full_descriptors))
        featurization_list.append(featurization)
        df = pd.DataFrame(featurization_list)

        df.to_csv(os.path.join(base_folder, 'full_featurization_frame.csv'))
        return df

def create_result_folder(mofname):
    '''Create a folder of the MOF where all the calculations and results will be saved'''
    new_folder = os.path.join(FOLDER_CALCULATED, mofname)
    if not os.path.exists(new_folder):
        os.mkdir(new_folder)
        print(f'New result folder created: {new_folder}')
    return new_folder

def initialze_models():
    Temperature_Model = MOF_prediction_models.TT_Model(target = 'temperature', target_unit = 'C')
    Time_Model = MOF_prediction_models.TT_Model(target = 'time', target_unit = 'h')
    Solvent_Model = MOF_prediction_models.Solvent_Model()
    Additive_Model = MOF_prediction_models.Additive_Model()

    return [Temperature_Model, Time_Model, Solvent_Model, Additive_Model ]

def unfold_summary_df(df:pd.DataFrame):
    for i, row in df.iterrows():
        if row['descriptors']:
            df.at[i, 'temperature_prediction'] = row['all_predictions'][0][0]
            df.at[i, 'temperature_prediction_certainty'] = row['all_predictions'][0][1]

            df.at[i, 'time_prediction'] = row['all_predictions'][1][0]
            df.at[i, 'time_prediction_certainty'] = row['all_predictions'][1][1]

            df.at[i, 'solvent_prediction'] = row['all_predictions'][2][0]
            df.at[i, 'solvent_prediction_certainty'] = row['all_predictions'][2][1]

            df.at[i, 'additive_prediction'] = row['all_predictions'][3][0]
            df.at[i, 'additive_prediction_certainty'] = row['all_predictions'][3][1]

    return df


def read_folder(folder):
    if not os.path.exists(folder):
        print(f'{folder} does not excist')
    
    cifs = [f for f in os.listdir(folder) if f.endswith('.cif')]    
    print(f'n files in \'{folder}\' : {len(os.listdir(folder))}')
    print(f'n cif files in \'{folder}\' : {len(cifs)}')

    full_paths = [os.path.join(folder, i) for i in cifs]
    return full_paths

all_cifs = read_folder(FOLDER)

overview_dict = {'name': [], 'descriptors': [], 'all_predictions' : []}

for i, cif in enumerate(all_cifs):
    print(f'-----{i +1 }/ {len(all_cifs)} -----')

    cif_object = CifFile(cif)
    MOF_name = cif_object.name

    res_folder = create_result_folder(MOF_name)

    descriptors_df = cif_object.get_descriptors(res_folder)


    if len(descriptors_df.columns) == 2:
        print(f"Could not calculate descriptors of {MOF_name}")
        all_predictions = []
        descriptors_bool = False

    else:
        descriptors_bool = True
        ML_models = initialze_models()
        for model in ML_models:
            model.make_predictions(MOF_name, descriptors_df)

        all_predictions = [model.get_final_prediction() for model in ML_models]
        
        print(all_predictions)
    
    overview_dict['name'].append(MOF_name)
    overview_dict['descriptors'].append(descriptors_bool)
    overview_dict['all_predictions'].append(all_predictions)

df_all = pd.DataFrame(overview_dict)
df_all = unfold_summary_df(df_all)

print(df_all)

now = datetime.now()
date_time_str = now.strftime("%Y%m%d_%H%M")
df_all.to_csv(f'{date_time_str}_predictions_all.csv')

#TODO: put everything in one CSV file