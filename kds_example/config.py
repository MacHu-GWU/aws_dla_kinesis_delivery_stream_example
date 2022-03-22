# -*- coding: utf-8 -*-

class Config:
    project_name = "kds_example"
    stage = "dev"
    oss_index_name = "bank_account"

    @property
    def project_name_slug(self):
        return self.project_name.replace("_", "-")

    @property
    def chalice_app_name(self):
        return self.project_name_slug

config = Config()
