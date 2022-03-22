# -*- coding: utf-8 -*-

class Config:
    project_name = "kds-example"
    oss_index_name = "bank_account"

    @property
    def project_name_slug(self):
        return self.project_name.replace("_", "-")


config = Config()

if __name__ == "__main__":
    print(config.project_name_slug)
