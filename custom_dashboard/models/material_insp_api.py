import datetime

from odoo import fields
from odoo.http import  request, root
from odoo.service import security
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from werkzeug.exceptions import BadRequest
from datetime import datetime , timedelta
import math, random
import logging
from odoo.http import request, route, Response
import json
from pytz import timezone
from odoo import http
import base64
_logger = logging.getLogger(__name__)


class SessionAuthenticationService(Component):
    _inherit = "base.rest.service"
    _name = "session.authenticate.service"
    _usage = "auth"
    _collection = "session.rest.services"

    @restapi.method([(["/maker/mi/update"], "POST")], auth="user")
    def update_mi_maker(self):
        # maker will update the checklist and click on submit button notification should sent to res. checker
        seq_no = 0
        params = request.params
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        #_logger.info("---------update_checklist_maker---------,%s", params)
        user_id = False
        send_notification = False
        overall_remarks = ''
        if params.get('is_draft'):
            #_logger.info("---------params--------,%s", params)

            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = int(params.get('user_id'))
        except:
            pass
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                    content_type='application/json;charset=utf-8', status=201)
        #activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        mi_id = self.env['material.inspection'].sudo().browse(int(params.get('mi_id')))

        if params.get('overall_remarks'):
            overall_remarks = params.get('overall_remarks')
            mi_id.write({'remark': overall_remarks})
       
        seq_no = mi_id.seq_no
        #_logger.info("-----seq_no-------,%s",seq_no)
       # _logger.info("----- params.get('checklist_line')-------,%s", params.get('checklist_line'))
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark'),'submitted':'false'})
                
                if send_notification:   
                    if line.get('is_pass') == 'nop' :
                        is_pass = 'na'
                    else:
                        is_pass = line.get('is_pass')

                    data = {'role':'maker','user_id':user_id,
                    'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_id.id,
                    'mi_line_id':checklist_id.id,'seq_no':seq_no,
                    'overall_remarks': overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(data)
        
        if send_notification:       
            mi_id.sudo().button_submit(seq_no,user_id)
    
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                    content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/mi/reject"], "POST")], auth="user")
    def reject_mi_checker(self):
        # Checker reject the checklist , notification to maker
        params = request.params
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
    
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        #_logger.info("---------update_checklist_reject_checker---------,%s", params)

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                    content_type='application/json;charset=utf-8', status=201)
        #activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        mi_id = self.env['material.inspection'].sudo().browse(int(params.get('mi_id')))

        if params.get('overall_remarks'):
            overall_remarks = params.get('overall_remarks')
            mi_id.write({'remark': overall_remarks})
       
        seq_no = mi_id.seq_no
        #_logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark'),'submitted':'false'})
                
                if send_notification:   
                    if line.get('is_pass') == 'nop' :
                        is_pass = 'na'
                    else:
                        is_pass = line.get('is_pass')

                    data = {'role':'maker','user_id':user_id,
                    'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_id.id,
                    'mi_line_id':checklist_id.id,'seq_no':seq_no,
                    'overall_remarks': overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(data)
        
        if send_notification:       
            mi_id.sudo().button_set_to_maker(seq_no,user_id)
        
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker Rejected'}),
                    content_type='application/json;charset=utf-8', status=200)


    @restapi.method([(["/checker/mi/update"], "POST")], auth="user")
    def update_mi_checker(self):
        # this method will get call from checekr to updte the checklist and submit. notification to approver
        params = request.params
        seq_no = False
        user_id = False
        send_notification = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = int(params.get('user_id'))
        except:
            pass
        #_logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                    content_type='application/json;charset=utf-8', status=201)
        #activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        mi_id = self.env['material.inspection'].sudo().browse(int(params.get('mi_id')))

        if params.get('overall_remarks'):
            overall_remarks = params.get('overall_remarks')
            mi_id.write({'remark': overall_remarks})
       
        seq_no = mi_id.seq_no
        #_logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark'),'submitted':'false'})
                
                if send_notification:   
                    if line.get('is_pass') == 'nop' :
                        is_pass = 'na'
                    else:
                        is_pass = line.get('is_pass')

                    data = {'role':'maker','user_id':user_id,
                    'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_id.id,
                    'mi_line_id':checklist_id.id,'seq_no':seq_no,
                    'overall_remarks': overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(data)
        

        if send_notification:
            mi_id.sudo().button_checking_done(seq_no,user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update','status':'Maker'}),
                    content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/reject"], "POST")], auth="user")
    def reject_mi_approver(self):
        # Approver will reject the checklist and go bakc to checker
        params = request.params
        #_logger.info("---------update_checklist_reject---------,%s", params)
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        #_logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                    content_type='application/json;charset=utf-8', status=201)
        #activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        mi_id = self.env['material.inspection'].sudo().browse(int(params.get('mi_id')))

        if params.get('overall_remarks'):
            overall_remarks = params.get('overall_remarks')
            mi_id.write({'remark': overall_remarks})
       
        seq_no = mi_id.seq_no
        #_logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark'),'submitted':'false'})
                
                if send_notification:   
                    if line.get('is_pass') == 'nop' :
                        is_pass = 'na'
                    else:
                        is_pass = line.get('is_pass')

                    data = {'role':'maker','user_id':user_id,
                    'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_id.id,
                    'mi_line_id':checklist_id.id,'seq_no':seq_no,
                    'overall_remarks': overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(data) 

        mi_id.sudo().button_set_to_checker(seq_no,user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Approver Rejected'}),
                    content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/update"], "POST")], auth="user")
    def update_mi_approver(self):
        # approver will update the checklist and notification to admin
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
       
        seq_no = False
        params = request.params
        #_logger.info("---------update_checklist_approver---------,%s,self", params,self)
        user_id = False
        send_notification = False
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = int(params.get('user_id'))
        except:
            pass
        #_logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                    content_type='application/json;charset=utf-8', status=201)
        #activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        mi_id = self.env['material.inspection'].sudo().browse(int(params.get('mi_id')))

        if params.get('overall_remarks'):
            overall_remarks = params.get('overall_remarks')
            mi_id.write({'remark': overall_remarks})
       
        seq_no = mi_id.seq_no
        #_logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark'),'submitted':'false'})
                
                if send_notification:   
                    if line.get('is_pass') == 'nop' :
                        is_pass = 'na'
                    else:
                        is_pass = line.get('is_pass')

                    data = {'role':'maker','user_id':user_id,
                    'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_id.id,
                    'mi_line_id':checklist_id.id,'seq_no':seq_no,
                    'overall_remarks': overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(data)
        
        if send_notification:
            mi_id.sudo().button_approve(seq_no,user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                    content_type='application/json;charset=utf-8', status=200)


    @restapi.method([(["/get/material/inspection"], "POST")], auth="user")
    def get_material_inspection(self):
        # if params contain checked_by(id) will send realted MI data otherwise all MI data.
        response= {}
        params = request.params

        if  not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Tower Id'}),
                            content_type='application/json;charset=utf-8', status=400)

        mi_data = self.env['material.inspection'].sudo().get_material_inspection(int(params.get('tower_id')))
        #mi_data = self.env['material.inspection'].sudo().get_material_inspection(125)

        response['material_inspection'] = mi_data
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Data Fetch','mi_data':response}),
                    content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/material/inspection"], "POST")], auth="user")
    def create_material_inspection(self):
        params = request.params
        #_logger.info("--create_duplicate_activities--params-1233333444-",params)
        if not params.get('project_info_id') and not params.get('tower_id') and not params.get('checked_by'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send project, tower id and Checked By(User) Id'}),
                            content_type='application/json;charset=utf-8', status=400)
        
        self.env['material.inspection'].sudo().create_material_inspection(params)
    
        return Response(
            json.dumps({'status': 'SUCCESS', 'message':'Material Inspection Created'}),
            content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/towers"], "POST")], auth="user")
    def get_project_towers(self):
        params = request.params
        if  not params.get('project_info_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Project Id'}),
                    content_type='application/json;charset=utf-8', status=201)
        
        towers = self.env['project.tower'].sudo().get_project_towers(int(params.get('project_info_id')))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetch','towers':towers}),
                    content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/mi/checklist"], "POST")], auth="user")
    def get_mi_checklist(self):
        checklist = self.env['mi.checklist'].sudo().get_mi_checklist()

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'MI Checklist Fetched','mi_checklist':checklist}),
                    content_type='application/json;charset=utf-8', status=200)


    @restapi.method([(["/delete/mi"], "POST")], auth="user")
    def delete_mi(self):
        params = request.params
        if  not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                    content_type='application/json;charset=utf-8', status=201)

        mi_rec = self.env['material.inspection'].browse(int(params.get('mi_id'))).unlink()
    
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection form deleted'}),
                    content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/mi"], "POST")], auth="user")
    def update_mi(self):
        params = request.params

        if  not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                    content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].update_mi(params)
    
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Updated Successfully'}),
                    content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/replicate/mi"], "POST")], auth="user")
    def replicate_mi(self):
        params = request.params
        _logger.info("----------params.get('mi_id')-------,%s",(params.get('mi_id')))

        if  not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                    content_type='application/json;charset=utf-8', status=201)
        mi_id =  params.get('mi_id')
        self.env['material.inspection'].replicate(int(mi_id))
    
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Replicate Successfully'}),
                    content_type='application/json;charset=utf-8', status=200)