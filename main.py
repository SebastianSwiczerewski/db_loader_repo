import sys
import os
import glob
import json
import pandas as pd
import multiprocessing
from dotenv import load_dotenv

load_dotenv()


def get_column_names(schemas, ds_name, sorting_key='column_position'):
    column_details = schemas[ds_name]
    columns = sorted(column_details, key=lambda col: col[sorting_key])
    return [col['column_name'] for col in columns]


def read_csv(file, schemas):
    file_path_list = file.split('/')
    ds_name = file_path_list[-2]
    columns = get_column_names(schemas, ds_name)
    df_reader = pd.read_csv(file, names=columns, chunksize=10000)
    return df_reader

def to_sql(df, db_conn_uri, ds_name):
    df.to_sql(
    ds_name,
    db_conn_uri,
    if_exists='append',
    index=False,
    method='multi'
)
    
def db_loader(src_base_dir, db_conn_uri, ds_name):
    schemas = json.load(open(f'{src_base_dir}/schemas.json'))
    files = glob.glob(f'{src_base_dir}/{ds_name}/part-*')
    if len(files) == 0:
        raise NameError(f'No files found for {ds_name}')
    
    for file in files:
        df_reader = read_csv(file, schemas)
        for idx, df in enumerate(df_reader):
            print(f'Populating chunk {idx} of {ds_name}')
            to_sql(df, db_conn_uri, ds_name)


def process_dataset(args):

    src_base_dir = args[0]
    db_conn_uri = args[1]
    ds_name = args[2]

    try:
        print(f'Processing {ds_name}')
        db_loader(src_base_dir, db_conn_uri, ds_name)
    except NameError as ne:
        print(ne)
        pass 
    except Exception as e:
        print(e)
        pass
    finally:
        print(f'Data Processing of {ds_name} is completed')


def process_files(ds_names=None):
    src_base_dir = os.environ.get('SRC_BASE_DIR')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_name = os.environ.get('DB_NAME')
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASS')
    db_conn_uri = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    schemas = json.load(open(f'{src_base_dir}/schemas.json'))
    
    if not ds_names:
        ds_names=schemas.keys()
    parallel_processes = len(ds_names) if len(ds_names) < 3 else 3
    pool = multiprocessing.Pool(parallel_processes)
    process_dataset_args = []
    for ds_name in ds_names:
       process_dataset_args.append((src_base_dir, db_conn_uri, ds_name))

    pool.map(process_dataset, process_dataset_args)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        ds_names = json.loads(sys.argv[1])
        process_files(ds_names)
    else:
        process_files()
