from odoo import models, api, fields, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
import random
from datetime import date
import datetime
from datetime import datetime, timedelta , time
from dateutil import parser
import re
import requests
import pytz
import json

class ResUsers(models.Model):
    _inherit = "res.users"

    player_line_ids = fields.One2many('app.notification', 'res_user_id', string='Player ID')


class AppNotificationLog(models.Model):
    _name = 'app.notification.log'
    _rec_name = "res_user_id"
    _order = 'notification_dt desc, id desc'
    _description = "AppNotificationLog"


    title = fields.Text('Title')
    notification_dt = fields.Datetime('DateTime',default=lambda self: fields.Datetime.now())
    read_unread = fields.Boolean('Is Read')
    res_user_id = fields.Many2one('res.users','To')
    project_info_id = fields.Many2one('project.info','Project')
    activity_type_id = fields.Many2one('project.activity.type','Activity Type')
    mi_id = fields.Many2one('material.inspection','Material Inspection')

    tower_id = fields.Many2one('project.tower','Tower')
    player_id = fields.Char("Player Id")
    message = fields.Text("Message")
    table_id = fields.Char("Checklist Id")
    seq_no = fields.Char("Seq No")
    status = fields.Selection([('sent', 'Sent'),('failed', 'Failed')],string="status")
    #overall_checklist_status = fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    #('approver_reject','Approver Rejected')],default='approve',string="Overall Checklist Status",readonly=1,store=True)
    checklist_status=fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    ('approver_reject','Approver Rejected')],default='draft',string="Checklist Status",readonly=1,store=True)
    checklist_status_two = fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    ('approver_reject','Approver Rejected')],default='draft',string="Checklist Status Two",readonly=1,store=True)
    detail_line = fields.Selection([('mi', 'MI'),('wi', 'WI')],string="Detail Line Value")
    resolved = fields.Boolean(default=False)

    def get_users_notification_details(self,user_id):
        #_logger.info("-------get_users_notification_details--------,%s,%s",(user_id,self.env.user.id))
        notifications = self.search([('res_user_id','=',self.env.user.id),('status','=','sent')])
        data = []
        if notifications:
            for notification in notifications:
                project_id = tower_id = status = ''
                activity_type_id = mi_id = False
                if notification.project_info_id:
                    project_id = notification.project_info_id.id
                if notification.tower_id:
                    tower_id = notification.tower_id.id 
                if notification.activity_type_id:
                    activity_type_id = notification.activity_type_id.id
                if notification.mi_id:
                    notification.mi_id.id

                ndata = {'mi_id':mi_id,'activity_type_id':activity_type_id,'checklist_status_two':notification.checklist_status_two or 'approve','checklist_status':notification.checklist_status or 'approve','tower_id':tower_id,'project_id':project_id,'detail_line':notification.detail_line or '','seq_no':notification.seq_no or 0,'id':notification.id,'title':notification.title,'notification_dt':str(notification.notification_dt),'redirect_id':notification.table_id or ''}
                data.append(ndata)
        return data
 
class AppNotification(models.Model):
    _name = 'app.notification'
    _order = 'id desc'
    _description = "AppNotification"


    notification_dt = fields.Datetime('DateTime',default=lambda self: fields.Datetime.now())
    res_user_id = fields.Many2one('res.users','Res Users')
    player_id = fields.Char("Player Id")
    datetime = fields.Datetime('Date Time',default=lambda self: fields.Datetime.now())
    table_id = fields.Char("Id")


    def send_push_notification(self,title,player_ids,message,user_ids,seq_no,insp_value,obj):
        # OneSignal API endpoint
        _logger.info("-----send_push_notification------,%s,%s,%s,%s",title,player_ids,message,user_ids)
        app_log_obj = self.env['app.notification.log']
        ck_status = ck_status_two = ''
        try:
            #onesignal_url = 'https://dashboard.onesignal.com/'
            project_id = tower_id = ''
            activity_type_id = False
            mi_id = False
            # For WI
            #_logger.info("--objobjobjobjobj---,%s",str(obj))

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
                
                for user_id ,player_id in zip(user_ids , player_ids):
                    app_log_obj.sudo().create({'mi_id':mi_id,'activity_type_id':activity_type_id,'detail_line':insp_value,'seq_no':seq_no,'status':'sent','title':title,'res_user_id':user_id,'player_id':player_id,'message':message,'table_id':obj.id,'project_info_id':project_id,'tower_id':tower_id,'checklist_status':ck_status,'checklist_status_two':ck_status_two})
                
                try:
                    if activity_type_id:
                        rec = app_log_obj.search([('activity_type_id','=',activity_type_id)])
                        if rec:
                            rec.write({'checklist_status':ck_status})
                except Exception as e:
                    _logger.info("---activity_type_idactivity_type_id exception notification-----,%s",str(e))
                    pass

                try:
                    if mi_id:
                        rec = app_log_obj.search([('mi_id','=',mi_id)])
                        if rec:
                            rec.write({'checklist_status':ck_status})
                except Exception as e:
                    _logger.info("---mi_idmi_idmi_idmi_id exception notification-----,%s",str(e))
                    pass


                return True
            else:
                for user_id ,player_id in zip(user_ids , player_ids):
                    app_log_obj.sudo().create({'mi_id':mi_id,'activity_type_id':activity_type_id,'detail_line':insp_value,'seq_no':seq_no,'status':'failed','title':title +' status code : '+str(response.status_code),'res_user_id':user_id,'player_id':player_id,'message':message,'table_id':obj.id,'project_info_id':project_id,'tower_id':tower_id,'checklist_status':ck_status,'checklist_status_two':ck_status_two})
                return True
        
        except Exception as e:
            _logger.info("---exception--------,%s",str(e))
            pass
           
    @api.model
    def updateDetailsOfOneSignal(self, domain=None, fields=None, limit=None, userId=None,openId=None,id=None,token=None,context=None):
        try:
            #self.env['res.users'].sudo().create({'res_user_id':userId,'player_id':id})
            user_record = self.env['res.users'].browse(userId)
            if user_record:
                child_records = [(0, 0, {'player_id': id})]
                user_record.write({
            'player_line_ids': child_records,
        })
                
        except Exception as ex:
            print ("--exception--",ex)
            self.env['error.log'].sudo().create({'model':'onesignal.notification','method_name':'updateDetailsOfOneSignal','datetime':datetime.now(),'error':str(ex)})
        response = {
            "status": 200,
            "message": "Meeting status updated successfully!"
        }
        return response

   