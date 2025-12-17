from odoo import api, fields, models, _


class ProjectInfo(models.Model):
    _inherit = 'project.info'

    def synch_projects_data(self):
        print('Cron Job--------')