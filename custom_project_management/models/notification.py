from datetime import datetime, timedelta, time
import json

from requests import request
import pytz
import requests
import re
from dateutil import parser
import datetime
from datetime import date
import random
from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    player_line_ids = fields.One2many(
        'app.notification', 'res_user_id', string='Player ID')


class AppNotificationLog(models.Model):
    _name = 'app.notification.log'
    _rec_name = "res_user_id"
    _order = 'notification_dt desc, id desc'
    _description = "AppNotificationLog"

    title = fields.Text('Title')
    notification_dt = fields.Datetime(
        'DateTime', default=lambda self: fields.Datetime.now())
    read_unread = fields.Boolean('Is Read')
    hide_notification = fields.Boolean('Hide Notification')
    res_user_id = fields.Many2one('res.users', 'To')
    project_info_id = fields.Many2one('project.info', 'Project')

    # activity_id = fields.Many2one('project.activity', 'Activity')
    # project_activity_name_id = fields.Many2one('project.activity', 'Activity')
    activity_type_id = fields.Many2one(
        'project.activity.type', 'Activity Type')
    # activity_id = fields.Many2one('project.activity.type', 'Activity Type')
    mi_id = fields.Many2one('material.inspection', 'Material Inspection')
    tower_id = fields.Many2one('project.tower', 'Tower')
    player_id = fields.Char("Player Id")
    message = fields.Text("Message")
    table_id = fields.Char("Checklist Id")
    seq_no = fields.Char("Seq No")
    status = fields.Selection(
        [('sent', 'Sent'), ('failed', 'Failed')], string="status")
    # overall_checklist_status = fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    # ('approver_reject','Approver Rejected')],default='approve',string="Overall Checklist Status",readonly=1,store=True)
    checklist_status = fields.Selection([('draft', 'Draft'), ('submit', 'Submit'), ('checked', 'Checked'), ('approve', 'Approved'), ('checker_reject', 'Checker Rejected'),
                                         ('approver_reject', 'Approver Rejected')], default='draft', string="Checklist Status", readonly=1, store=True)
    checklist_status_two = fields.Selection([('draft', 'Draft'), ('submit', 'Submit'), ('checked', 'Checked'), ('approve', 'Approved'), ('checker_reject', 'Checker Rejected'),
                                             ('approver_reject', 'Approver Rejected')], default='draft', string="Checklist Status Two", readonly=1, store=True)
    detail_line = fields.Selection(
        [('mi', 'MI'), ('wi', 'WI')], string="Detail Line Value")

    @api.model
    def action_hide_notification(self):
        _logger.info("===========action_hide_notification===========called")
        active_ids = self.env.context.get('active_ids')

        if not active_ids:
            _logger.warning("No records selected for Hide.")
            return

        records = self.browse(active_ids).filtered(
            lambda r: r.activity_type_id and r.activity_type_id.status == 'approve')
        if records:
            records.write({'hide_notification': True})

    
    def hide_checker_notifications_on_approval(self, checklist_id):
        """
        Hides notifications for checkers related to a specific checklist once it's approved.
        """
        _logger.info("Running hide_checker_notifications_on_approval for checklist ID: %s", checklist_id)

        logs_to_hide = self.search([
            ('table_id', '=', str(checklist_id)),  # assuming checklist ID is stored in table_id
            ('hide_notification', '=', False),
            '|',
            ('checklist_status', '=', 'approve'),
            ('checklist_status_two', '=', 'approve'),
        ])

        if logs_to_hide:
            logs_to_hide.write({'hide_notification': True})
            _logger.info("Notifications hidden for logs: %s", logs_to_hide.ids)
        else:   
            _logger.info("No notifications found to hide for checklist ID: %s", checklist_id)




   
    # def create_nc_notification(self, nc, project_responsible):
    #     """Creates a notification for NC in app.notification.log."""
    #     _logger.warning("No responsible user found for NC notification.")
    #     if not project_responsible:
    #         _logger.warning("No responsible user found for NC notification.")
    #         return

    #     notification_vals = {
    #         'res_user_id': project_responsible,
    #         'status': 'nc',
    #         'title': 'New NC Created',
    #         'notification_dt': fields.Datetime.now(),
    #         'seq_no': nc.id,
    #         'hide_notification': False,
    #     }

    #     # Ensure `detail_line` is valid (change to Text field if needed)
    #     if 'detail_line' in self._fields and self._fields['detail_line'].type == 'selection':
    #         # Use valid selection value
    #         notification_vals['detail_line'] = 'mi'
    #     else:
    #         notification_vals[
    #             'detail_line'] = f"A new NC has been created for project {nc.project_info_id.name}."

    #     try:
    #         notification = self.env['app.notification.log'].sudo().create(
    #             notification_vals)
    #         _logger.info(f"NC Notification Created: ID {notification.id}")
    #     except Exception as e:
    #         _logger.error(f"Failed to create NC notification: {str(e)}")

    def get_users_notification_details(self, user_id):

        notifications = self.search([
            ('res_user_id', '=', self.env.user.id),
            ('status', '=', 'sent'),
            ('hide_notification', '=', False)
        ])

        # Fetch NC notifications (modify filter conditions if needed)
        nc_notifications = self.search([
            ('res_user_id', '=', self.env.user.id),
            ('status', '=', 'sent'),  # Assuming 'nc' is a valid status
            ('hide_notification', '=', False)
        ])

        all_notifications = notifications | nc_notifications  # Combine both

        data = []
        for notification in all_notifications:
            project_id = tower_id = status = ''
            activity_type_id = mi_id = False
            activity_id = activity_name = None

            # seq_no = notification.seq_no or 0

            if notification.project_info_id:
                project_id = notification.project_info_id.id
            if notification.tower_id:
                tower_id = notification.tower_id.id
            if notification.activity_type_id:
                activity_type_id = notification.activity_type_id.id
                activity_id = notification.activity_type_id.activity_id.id if notification.activity_type_id.activity_id else False
                activity_name = notification.activity_type_id.activity_id.name if notification.activity_type_id.activity_id else False
            if notification.mi_id:
                mi_id = notification.mi_id.id

            ndata = {
                'mi_id': mi_id,
                'activity_type_id': activity_type_id,
                'checklist_status_two': notification.checklist_status_two or 'approve',
                'checklist_status': notification.checklist_status or 'approve',
                'activity_id': activity_id,
                'tower_id': tower_id,
                'activity_name': activity_name,
                'project_id': project_id,
                'detail_line': notification.detail_line or '',
                'seq_no': notification.seq_no or 0,
                # 'seq_no': seq_no,
                'id': notification.id,
                'title': notification.title,
                'notification_dt': str(notification.notification_dt),
                'redirect_id': notification.table_id or '',
                'nc_id': notification.table_id or '',  # Add this to send nc.id in response
            }

            _logger.info("-------nadata------%s", ndata)
            data.append(ndata)

        return data


class AppNotification(models.Model):
    _name = 'app.notification'
    _order = 'id desc'
    _description = "AppNotification"

    notification_dt = fields.Datetime(
        'DateTime', default=lambda self: fields.Datetime.now())
    res_user_id = fields.Many2one('res.users', 'Res Users')
    player_id = fields.Char("Player Id")
    datetime = fields.Datetime(
        'Date Time', default=lambda self: fields.Datetime.now())
    table_id = fields.Char("Id")

    def send_push_notification(self, title, player_ids, message, user_ids, seq_no, insp_value, obj):
        # OneSignal API endpoint
        _logger.info("-----send_push_notification------,%s,%s,%s,%s",
                     title, player_ids, message, user_ids)
        app_log_obj = self.env['app.notification.log']
        ck_status = ck_status_two = ''
        try:
            # onesignal_url = 'https://dashboard.onesignal.com/'
            project_id = tower_id = ''
            activity_type_id = False
            mi_id = False
            # For WI
            # _logger.info("--objobjobjobjobj---,%s",str(obj))

            try:
                if obj:
                    if obj.project_id:
                        project_id = obj.project_id.id
                    if obj.tower_id:
                        tower_id = obj.tower_id.id
                    ck_status = obj.status or ''
                    ck_status_two = obj.type_status or ''
                    activity_type_id = obj.id

            except:
                pass
            # For MI
            try:
                if obj:
                    if obj.project_info_id:
                        project_id = obj.project_info_id.id
                    if obj.tower_id:
                        tower_id = obj.tower_id.id
                    ck_status = obj.status or ''
                    ck_status_two = obj.mi_status or ''
                    mi_id = obj.id

            except:
                pass

            app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
            rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

            # Notification contents

            # Data to send in the notification
            data = {
                "app_id": app_id,
                "include_player_ids": [player_ids[0]],
                "contents": {"en": message},
                "headings": {"en": title},
            }

            # Convert data to JSON
            data_json = json.dumps(data)

            # URL for OneSignal REST API
            url = "https://onesignal.com/api/v1/notifications"

            # Headers for the request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {rest_api_key}"
            }

            # Send the notification
            response = requests.post(url, data=data_json, headers=headers)

            if response.status_code == 200:

                for user_id, player_id in zip(user_ids, player_ids):
                    app_log_obj.sudo().create({'mi_id': mi_id, 'activity_type_id': activity_type_id, 'detail_line': insp_value, 'seq_no': seq_no, 'status': 'sent', 'title': title, 'res_user_id': user_id,
                                               'player_id': player_id, 'message': message, 'table_id': obj.id, 'project_info_id': project_id, 'tower_id': tower_id, 'checklist_status': ck_status, 'checklist_status_two': ck_status_two})

                try:
                    if activity_type_id:
                        rec = app_log_obj.search(
                            [('activity_type_id', '=', activity_type_id)])
                        if rec:
                            rec.write({'checklist_status': ck_status})
                except Exception as e:
                    _logger.info(
                        "---activity_type_idactivity_type_id exception notification-----,%s", str(e))
                    pass

                try:
                    if mi_id:
                        rec = app_log_obj.search([('mi_id', '=', mi_id)])
                        if rec:
                            rec.write({'checklist_status': ck_status})
                except Exception as e:
                    _logger.info(
                        "---mi_id mi_id mi_id mi_id exception notification-----,%s", str(e))
                    pass

                return True
            else:
                for user_id, player_id in zip(user_ids, player_ids):
                    app_log_obj.sudo().create({'mi_id': mi_id, 'activity_type_id': activity_type_id, 'detail_line': insp_value, 'seq_no': seq_no, 'status': 'failed', 'title': title + ' status code : '+str(response.status_code),
                                               'res_user_id': user_id, 'player_id': player_id, 'message': message, 'table_id': obj.id, 'project_info_id': project_id, 'tower_id': tower_id, 'checklist_status': ck_status, 'checklist_status_two': ck_status_two})
                return True

        # except Exception as e:
        #     _logger.info("---exception--------,%s", str(e))
        #     pass

        except Exception as e:
            _logger.exception("Notification failed")
            return {"success": False, "error": str(e)}


    @api.model
    def updateDetailsOfOneSignal(self, domain=None, fields=None, limit=None, userId=None, openId=None, id=None, token=None, context=None):
        try:
            # self.env['res.users'].sudo().create({'res_user_id':userId,'player_id':id})
            user_record = self.env['res.users'].browse(userId)
            if user_record:
                child_records = [(0, 0, {'player_id': id})]
                user_record.write({
                    'player_line_ids': child_records,
                })

        except Exception as ex:
            _logger.info(
                "--updateDetailsOfOneSignal-exception--------,%s", str(ex))

            # self.env['error.log'].sudo().create(
            #     {'model': 'onesignal.notification', 'method_name': 'updateDetailsOfOneSignal', 'datetime': datetime.now(), 'error': str(ex)})
        response = {
            "status": 200,
            "message": "Updated Successfully!"
        }
        return response
