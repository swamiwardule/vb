# -*- coding: utf-8 -*-
# from distutils.command.check import check
# from setuptools import setup
# from setuptools.command.check import check

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class ProjectReport(models.Model):
    _name = 'project.report'
    _description = "Project Report"

    project_info_id = fields.Many2one(string='Project',comodel_name='project.info')
    tower_ids = fields.Many2many('project.tower',string = 'Tower')

    def action_print_report(self):
        # Example dictionary data
        custom_data = {
            'Project Name': 'Safety Enhancement',
            'Location': 'Building A',
            'Observation 1': 'Ceiling block hanging dangerously',
            'Issued To': 'Safety Department',
            'Target Date': 'N/A',
        }

        # Pass the dictionary to the report
        data = {
            'docs': [{'custom_data': custom_data}]
        }

        return self.env.ref('report.report_project_report_action').report_action(self, data=data)



    def action_print_report1(self):
        data = {
            'docs': self,  # Pass the current record(s) here
            'project_info_id': self.project_info_id.name,
            'tower_ids': self.tower_ids,
            'lines': [
                {
                    'sr_no': 1,
                    'safety_concerns': 'Example Concern',
                    'image': base64.b64encode(b'some_image_data').decode(),  # Example image data
                    'issued_to': 'John Doe',
                    'target_date': '2024-08-15',
                },
                # Add more lines as needed
            ]
        }
       
        _logger.info("---data------,%s",str(data))

        # Generate the report
        return self.env.ref('report.report_project_report_action').report_action(self, data=data)