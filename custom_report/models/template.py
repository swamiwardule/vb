from odoo import models, fields, api
import json
from odoo.http import request, root
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger("_name_")


class ChecklistReportGenerator(models.Model):
    _name = "template.detail"
    _description = "Template Details"

    name = fields.Many2one('project.info', string="Project", required=True)
    tower_id = fields.Many2one('project.tower', string="Tower", required=True)
    selection = fields.Selection([
        ('floor', 'Floor'),
        ('flat', 'Flat')
    ], string='Select Floor or Flat', default='floor')

    floor_id = fields.Many2one('project.floors', string='Floor')
    flat_id = fields.Many2one('project.flats', string='Flat')
    activity_id = fields.Many2one(
        'project.activity', string="Activity", required=True)
    location = fields.Char(string="Location")
    date = fields.Date(string="Date")

    checklines = fields.Char(string="Checklist Lines")
    user_maker = fields.Many2one('res.users', string="Maker")
    user_checker = fields.Many2one('res.users', string="Checker")
    user_approver = fields.Many2one('res.users', string="Approver")
    activity_users = fields.Char(string="Users")

    def clear_fields(self):
        self.selection = 'floor'
        self.floor_id = False
        self.flat_id = False
        self.location = False
        self.date = False
        self.checklines = False
        self.user_maker = False
        self.user_checker = False
        self.user_approver = False

    @api.onchange('name')
    def _onchange_project(self):
        if self.name:
            return {'domain': {'tower_id': [('project_id', '=', self.name.id)]}}
        else:
            return {'domain': {'tower_id': []}}

    @api.onchange('tower_id')
    def _onchange_tower(self):
        if self.tower_id:
            return {
                'domain': {
                    'floor_id': [('tower_id', '=', self.tower_id.id)],
                    'flat_id': [('tower_id', '=', self.tower_id.id)]
                }
            }
        else:
            return {'domain': {'floor_id': [], 'flat_id': []}}

    @api.onchange('selection')
    def _onchange_selection(self):
        if self.selection == 'floor':
            self.flat_id = False
        elif self.selection == 'flat':
            self.floor_id = False

    @api.onchange('floor_id')
    def _onchange_floor(self):
        if self.floor_id:
            return {
                'domain': {'activity_id': [('floor_id', '=', self.floor_id.id)]}
            }
        else:
            return {'domain': {'activity_id': []}}

    @api.onchange('flat_id')
    def _onchange_flat(self):
        if self.flat_id:
            return {
                'domain': {'activity_id': [('flat_id', '=', self.flat_id.id)]}
            }
        else:
            return {'domain': {'activity_id': []}}


# function to print report

    def print_report(self):

        self.fetch_checklist_data_and_users()
        return self.env.ref('custom_report.report_print').report_action(self)

# function to fetch checklist lines
    def fetch_checklist_data(self):
        if not self.activity_id:
            raise ValueError("Please select an activity first.")

        master_lst = []
        project_id = self.name.id
        tower_id = self.tower_id.id
        activity_id = self.activity_id.id

        domain = [
            ('project_activity_id', '=', activity_id),
            ('project_id', '=', project_id),
            ('tower_id', '=', tower_id)
        ]

        activities = self.env['project.activity'].search(domain)
        # _logger.warning("Found activities: %s", activities)

        checklist_lines = []
        for activity_type in self.activity_id.activity_type_ids:
            # print("----activity_typeactivity_typeactivity_type------",
            #       activity_type.id)
            # _logger.info(
            #     "activity_typeactivity_typeactivity_type: %s", activity_type.id)
            

            submitted_date = activity_type.submitted_date or ''
            if submitted_date:
                formatted_date = submitted_date.strftime('%d-%m-%Y')
            else:
                formatted_date = ''

            act_name = activity_type.project_activity_type_id.name
            for index, checklist in enumerate(activity_type.project_activity_type_id.checklist_ids):
                is_last = index == len(activity_type.project_activity_type_id.checklist_ids) - 1

                checklist_info = {
                    "act_name": act_name,
                    "index": index + 1,
                    "name": checklist.checklist_template_id.name,
                    "is_pass": checklist.is_pass,
                    "reason": checklist.reason,
                    'submitted_date': str(formatted_date),
                    "temp": 'true' if is_last else 'false',
                }
                checklist_lines.append(checklist_info)

        self.checklines = json.dumps(checklist_lines)

        return {'checklines': checklist_lines}

# function to fetch users of specific activity type
    def get_users(self):
        if not self.activity_id or not self.tower_id:
            raise ValueError(
                "Activity ID and Tower ID are required to fetch users.")

        activities = self.env['project.activity.type'].search([
            ('activity_id', '=', self.activity_id.id),
            ('tower_id', '=', self.tower_id.id),
            ('project_id', '=', self.name.id)
        ])

        if not activities:

            raise UserError(
                "No activities found for the given Activity and Tower.")

        activity_users = []
        
        for activity in activities:
            
            user_maker = activity.user_maker.name or ''
            user_checker = activity.user_checker.name or ''
            user_approver = activity.user_approver.name or ''

            user_maker = self.env['res.users'].search(
                [('name', '=', user_maker)], limit=1)
            user_checker = self.env['res.users'].search(
                [('name', '=', user_checker)], limit=1)
            user_approver = self.env['res.users'].search(
                [('name', '=', user_approver)], limit=1)

            # _logger.info("Activity: %s", activity.name)
            # _logger.info("-----maker----%s", user_maker.name if user_maker else 'None')
            # _logger.info("-----checker----%s", user_checker.name if user_checker else 'None')
            # _logger.info("-----approver----%s", user_approver.name if user_approver else 'None')

            activity_users.append({
                'activity_name': activity.name,
                'user_maker': user_maker.name if user_maker else '',
                'user_checker': user_checker.name if user_checker else '',
                'user_approver': user_approver.name if user_approver else ''
            })
       
        # Store the result as JSON string if needed
        self.activity_users = json.dumps(activity_users)

        return {'activity_users': activity_users}

    def fetch_checklist_data_and_users(self):

        self.fetch_checklist_data()    # Fetch checklist data
        self.get_users()        # Fetch users data

        return True
