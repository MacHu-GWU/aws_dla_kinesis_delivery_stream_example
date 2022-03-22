# -*- coding: utf-8 -*-

import json
from pathlib import Path
import kds_example
from kds_example.boto_ses import aws_account_id, aws_region
from kds_example.config import config
from kds_example.iac.s2_app import stack

chalice_config = {
    "version": "2.0",
    "app_name": kds_example.__chalice_app_name__,
    "stages": {
        "dev": {
            "lambda_memory_size": 512,
            "lambda_timeout": 30,
            "manage_iam_role": False,
            "iam_role_arn": f"arn:aws:iam::{aws_account_id}:role/{stack.iam_role_name_for_lbd}",
            "layers": [
                f"arn:aws:lambda:{aws_region}:{aws_account_id}:layer:{config.project_name_slug}:1"
            ],
        }
    }
}

dir_here = Path(__file__).absolute().parent
path_chalice_config = Path(dir_here, ".chalice", "config.json")
path_chalice_config.write_text(
    json.dumps(chalice_config, indent=4), encoding="utf-8"
)
