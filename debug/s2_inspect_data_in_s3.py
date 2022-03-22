# -*- coding: utf-8 -*-

import pandas as pd
from s3pathlib import S3Path
from kds_example.config import config
from kds_example.iac.s2_app import stack

pd.options.display.max_columns = 1000
pd.options.display.width = 1000

s3path_to_s3_01_backup = S3Path(stack.s3_data_bucket_name, "to-s3", "01-backup/")
s3path_to_s3_02_backup_failed = S3Path(stack.s3_data_bucket_name, "to-s3", "02-backup-failed/")
s3path_to_s3_03_success = S3Path(stack.s3_data_bucket_name, "to-s3", "03-success/")
s3path_to_s3_04_failed = S3Path(stack.s3_data_bucket_name, "to-s3", "04-failed/")
s3path_to_oss_01_backup = S3Path(stack.s3_data_bucket_name, "to-oss", "01-backup/")
s3path_to_oss_02_backup_failed = S3Path(stack.s3_data_bucket_name, "to-oss", "02-backup-failed/")


def count_records_in_s3_folder(s3path):
    return sum([
        sp.read_text().count("\n")
        for sp in s3path.iter_objects()
    ])


# --- Count file number
# print(f"{s3path_to_s3_01_backup.key} has {s3path_to_s3_01_backup.count_objects()} files")
# print(f"{s3path_to_s3_02_backup_failed.key} has {s3path_to_s3_02_backup_failed.count_objects()} files")
# print(f"{s3path_to_s3_03_success.key} has {s3path_to_s3_03_success.count_objects()} files")
# print(f"{s3path_to_s3_04_failed.key} has {s3path_to_s3_04_failed.count_objects()} files")
# print(f"{s3path_to_oss_01_backup.key} has {s3path_to_oss_01_backup.count_objects()} files")
# print(f"{s3path_to_oss_02_backup_failed.key} has {s3path_to_oss_02_backup_failed.count_objects()} files")

# --- Count record number
# print(f"{s3path_to_s3_01_backup.key} has {count_records_in_s3_folder(s3path_to_s3_01_backup)} records")
# print(f"{s3path_to_s3_02_backup_failed.key} has {count_records_in_s3_folder(s3path_to_s3_02_backup_failed)} records")
# print(f"{s3path_to_s3_03_success.key} has {count_records_in_s3_folder(s3path_to_s3_03_success)} records")
# print(f"{s3path_to_s3_04_failed.key} has {count_records_in_s3_folder(s3path_to_s3_04_failed)} records")
# print(f"{s3path_to_oss_01_backup.key} has {count_records_in_s3_folder(s3path_to_oss_01_backup)} records")
# print(f"{s3path_to_oss_02_backup_failed.key} has {count_records_in_s3_folder(s3path_to_oss_02_backup_failed)} records")

# --- Preview file content
# print(s3path_to_s3_01_backup.iter_objects().one().read_text())
# print(s3path_to_s3_02_backup_failed.iter_objects().one().read_text())
# print(s3path_to_s3_03_success.iter_objects().one().read_text())
# print(s3path_to_s3_04_failed.iter_objects().one().read_text())
# print(s3path_to_oss_01_backup.iter_objects().one().read_text())
# print(s3path_to_oss_02_backup_failed.iter_objects().one().read_text())

# --- Clear all data in s3 bucket
# S3Path(stack.s3_data_bucket_name, "/").delete_if_exists()
