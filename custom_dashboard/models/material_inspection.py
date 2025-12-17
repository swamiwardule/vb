# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request
import json
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)
import base64


# class ProjectInfo(models.Model):
#     _inherit = 'project.info'
#     #_rec_name = 'name'

#     material_inspection_line = fields.One2many('material.inspection', 'project_info_id')

class MaterialInspection(models.Model):
    _name = 'material.inspection'
    _rec_name = 'project_info_id'
    _description = "MaterialInspection"

    

    seq_no = fields.Char("Sequence No")
    material_insp_line = fields.One2many('material.inspection.line','material_insp','Material Insp Line')
    material_insp_log = fields.One2many('material.inspection.log','mi_id','Material Insp Log')
    material_insp_img = fields.One2many('material.inspection.images','mi_id','Material Insp Image')
    company_name = fields.Char('Comapny Name')
    title = fields.Char('Title')
    mir_no = fields.Char('MIR No')
    supplier_name = fields.Char('Supplier Name')
    project_name = fields.Char('Project Name')
    material_desc = fields.Char('Material Description')
    invoice_no = fields.Char('Challan/Invoice No')
    quality_as_per_challan_inv = fields.Char('Quality as per Challan / Invoice')
    date_of_material = fields.Date('Date of Material Received at Site')
    vehicle_no = fields.Char('Vehicle No')
    batch_no = fields.Char('Bathch / Week / Lot No')
    date_of_insp = fields.Date('Date of Inspection')
    remark = fields.Char('Remark')
    checked_by = fields.Many2one('res.users','Checked By')
    tower_id = fields.Many2one('project.tower','Tower')
    project_info_id = fields.Many2one('project.info','Project')
    image = fields.Binary('Image')
    status=fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved')],default='draft',string="Status")
    checked_date = fields.Datetime("Checked Date")
    approved_date = fields.Datetime('Approved Date')
    user_maker = fields.Many2one('res.users','Maker')
    user_checker = fields.Many2one('res.users','Checker')
    user_approver = fields.Many2one('res.users','Approver')
    mi_status=fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved'),('checker_reject','Checker Rejected'),
    ('approver_reject','Approver Rejected')],default='draft',string="Mi Status")
    #image_ids = fields.Many2many('product.image', string='Images')
    #image_ids = fields.Many2many('material.inspection', 'mi_image_rel', 'mi_id', 'image_id', string='Images')

    #project_info_id = fields.Many2one('project.info','Project Id')

    def replicate(self,mi_id):
        #_logger.info("---------replicate---------,%s,self", params,self)

        rec = self.browse(mi_id)
        if rec:
            #_logger.info("----------replicate-------,%s",(rec.tower_id))

            replicate = {
                "tower_id":rec.tower_id.id or False,
                "project_info_id":rec.project_info_id.id or False,
                "company_name": rec.company_name or '',
                "mir_no": rec.mir_no or '',
                "supplier_name": rec.supplier_name or '',
                "project_name": rec.project_name or '',
                "material_desc": rec.material_desc or '',
                "invoice_no": rec.invoice_no or '',
                "quality_as_per_challan_inv": rec.quality_as_per_challan_inv or '',
                "vehicle_no": rec.vehicle_no or '',
                "date_of_insp": rec.date_of_insp or '',
                "date_of_material": rec.date_of_material or '',
                "batch_no": rec.batch_no or '',
                "remark": rec.remark or '',
                "checked_by": rec.checked_by.id or '',
                "image":rec.image or False,
            }
            #_logger.info("----------replicate-------,%s",(replicate))

            seq_no = self.env['material.inspection.seq'].get_or_create_seq_no(rec.project_info_id.id)
            replicate.update({'seq_no':seq_no})

            repl_id = self.create(replicate)
            line_lst = []
            for line in rec.material_insp_line:
                line_lst.append({'material_insp':repl_id.id,'checklist_id':line.checklist_id.id or False,'observation':line.observation,'remark':line.remark})
            if line_lst:
                self.env['material.inspection.line'].create(line_lst)

        return
            
    def update_mi(self,data):
        #_logger.info("---------update_mi---------,%s,self", params,self)

        rec = self.browse(int(data['mi_id']))
        if rec:
            if 'tower_id' in data:
                rec.tower_id = int(data['tower_id'])
        
            if 'project_info_id' in data:
                rec.project_info_id = int(data['project_info_id'])
            if 'company_name' in data:
                rec.company_name = data['company_name']
            if 'mir_no' in data:
                rec.mir_no = data['mir_no']
            if 'supplier_name' in data:
                rec.supplier_name = data['supplier_name']
            if 'project_name' in data:
                rec.project_name = data['project_name']
            if 'material_description' in data:
                rec.material_desc = data['material_description']
            if 'invoice_no' in data:
                rec.invoice_no = data['invoice_no']
            if 'quantity_as_invoice' in data:
                rec.quality_as_per_challan_inv = data['quantity_as_invoice']
            if 'vehicle_no' in data:
                rec.vehicle_no = data['vehicle_no']
            if 'date_of_inspection' in data:
                rec.date_of_insp = data['date_of_inspection']
            if 'date_of_material_received' in data:
                rec.date_of_material = data['date_of_material_received']
            if 'batch_no' in data:
                rec.batch_no = data['batch_no']
            if 'overall_remark' in data:
                rec.remark = data['overall_remark']
            if 'check_by' in data:
                rec.checked_by = int(data['check_by'])
            if 'image' in data:
                rec.image = data['image']

            try:
                for image in data['image_data']:
                    new_image = self.env['material.inspection.images'].create({
                    'image': image,
                    'filename': str(fields.Datetime.now()),
                    'mi_id':rec.id, })
                    #image_ids.append(new_image.id)
            except Exception as e:
                    _logger.info("---MI Imags--exception---------,%s",str(e))
                    pass

            for line in data['checklist_data']:
                mi_line = self.env['material.inspection.line'].search([('material_insp','=',rec.id),('id','=',int(line['id']))])
                if mi_line:
                    mi_line.checklist_id = int(line['mi_checklist_id'])
                    mi_line.observation = line['is_pass']
                    mi_line.remark = line['remark']
    #
    def update_mi_maker(self,params):
        #_logger.info("---------update_mi_maker----params-----,%s", params)

        seq_no = 0
        user_id = False
        send_notification = False
        
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
    
        user_id = int(params.get('user_id'))
      
        mi_id = self.browse(int(params.get('mi_id')))
        overall_remark = ''
        if params.get('overall_remark'):
            overall_remark = params.get('overall_remark')
            mi_id.write({'remark': overall_remark})
        if params.get('image'):
            mi_id.write({'image': params.get('image')})
        
        if mi_id and user_id:
            mi_id.user_maker = user_id
       
        seq_no = mi_id.seq_no
        log_data = []
        # try:
        #     _logger.info("--params.get('image_data')--------,%s",str(params.get('image_data')))
        # except Exception as e:
        #         _logger.info("---MI Imags--exception---------,%s",str(e))
        #         pass


        try:
            for image in params.get('image_data'):
                new_image = self.env['material.inspection.images'].create({
                'image': image,
                'filename': str(fields.Datetime.now()),
                'mi_id':mi_id.id, })
                #image_ids.append(new_image.id)
        except Exception as e:
                _logger.info("---MI Imags--exception---------,%s",str(e))
                pass
        
        if params.get('checklist_line'):
            #checklist_image_url=base_url+"/web/image?model=material.inspection&field=image&id="+str(mi_id.id)
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                remark = ''
                if checklist_id:
                    remark = line.get('remark')                    
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark')})
                
                # if send_notification:   
                #     if line.get('is_pass') == 'nop' :
                #         is_pass = 'na'
                #     else:
                #         is_pass = line.get('is_pass')

                    # logdata = {'role':'maker','user_id':user_id,'checklist_id':checklist_id.id,
                    # 'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_info_id.id,
                    # 'seq_no':seq_no,'remark':remark,'status':'submit',
                    # 'overall_remarks': overall_remark or mi_id.remark,'image':mi_id.image}
                    # log_data.append(logdata)

                    #mi_log = self.env['material.inspection.log'].create(data)
                    #mi_id.material_insp_log = [(6, 0, [mi_log.id])]
                    #mi_log.url=base_url+"/web/image?model=material.inspection.log&field=image&id="+str(mi_log.id)

        # if log_data:
        #     child_records = [(0, 0, data) for data in log_data] 
        #     mi_id.write({'material_insp_log': child_records})
        if send_notification:       
            mi_id.sudo().button_submit(seq_no,user_id)
        return 
    

    def reject_mi_checker(self,params):
        #_logger.info("---------reject_mi_checker---------,%s,self", params,self)


        send_notification = False
        
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        user_id = int(params.get('user_id'))
        mi_id = self.browse(int(params.get('mi_id')))
        if params.get('overall_remark'):
            overall_remark = params.get('overall_remark')
            mi_id.write({'remark': overall_remark})
        user_id = int(params.get('user_id'))
        if mi_id and user_id:
            mi_id.user_checker =user_id
       
        seq_no = mi_id.seq_no
        log_data = []
        try:
            for image in params.get('image_data'):
                new_image = self.env['material.inspection.images'].create({
                'image': image,
                'filename': str(fields.Datetime.now()),
                'mi_id':mi_id.id, })
                #image_ids.append(new_image.id)
        except Exception as e:
                _logger.info("---MI Imags--exception---------,%s",str(e))
                pass
       
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark')})
                
                    # if line.get('is_pass') == 'nop' :
                    #     is_pass = 'na'
                    # else:
                    #     is_pass = line.get('is_pass')

                    # logdata = {'role':'checker','user_id':user_id,'checklist_id':checklist_id.id,
                    # 'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_info_id.id,
                    # 'seq_no':seq_no,'remark':line.get('remark'),'status':'draft',
                    # 'overall_remarks': overall_remarks}
                    # log_data.append(logdata)
                    #mi_log = self.env['material.inspection.log'].create(data)
                    #mi_log.url=base_url+"/web/image?model=material.inspection.log&field=image&id="+str(mi_log.id)
        #_logger.info("---------update_checklist_reject_checker---------,%s", kkk)
        
        # if log_data:
        #     child_records = [(0, 0, data) for data in log_data] 
        #     mi_id.write({'material_insp_log': [(4, 0, 0)] + child_records})
        if send_notification:
            mi_id.sudo().button_set_to_maker(seq_no,user_id)
        return
    def reject_mi_approver(self,params):
        #_logger.info("---------reject_mi_approver---------,%s,self", params,self)

        send_notification = False
        
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        
        user_id = int(params.get('user_id'))
        mi_id = self.browse(int(params.get('mi_id')))
        overall_remark = ''
        if params.get('overall_remark'):
            overall_remark = params.get('overall_remark')
            mi_id.write({'remark': overall_remark})
        
        
        mi_id.user_approver = user_id
       
        seq_no = mi_id.seq_no
        log_data = []

        try:
            for image in params.get('image_data'):
                new_image = self.env['material.inspection.images'].create({
                'image': image,
                'filename': str(fields.Datetime.now()),
                'mi_id':mi_id.id, })
                #image_ids.append(new_image.id)
        except Exception as e:
                _logger.info("---MI Imags--exception---------,%s",str(e))
                pass
        #_logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark')})
                
               
                    # if line.get('is_pass') == 'nop' :
                    #     is_pass = 'na'
                    # else:
                    #     is_pass = line.get('is_pass')

        #             logdata = {'role':'approver','user_id':user_id,'checklist_id':checklist_id.id,
        #             'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_info_id.id,
        #             'seq_no':seq_no,'remark':line.get('remark'),'status':'submit',
        #             'overall_remark': overall_remark or mi_id.remark,'image':mi_id.image}
        #             log_data.append(logdata)

        # if log_data:
        #     child_records = [(0, 0, data) for data in log_data] 
        #     mi_id.write({'material_insp_log': child_records})
        if send_notification:
            mi_id.sudo().button_set_to_checker(seq_no,user_id)
        return 

    def update_mi_approver(self,params):
        #_logger.info("---------update_mi_approver---------,%s,self", params,self)

        seq_no = False

        #_logger.info("---------update_checklist_approver---------,%s,self", params,self)
        user_id = False
        send_notification = False
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        
        user_id = int(params.get('user_id'))
       
        #activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        mi_id = self.browse(int(params.get('mi_id')))
        overall_remark = ''
        if params.get('overall_remark'):
            overall_remark = params.get('overall_remark')
            mi_id.write({'remark': overall_remark})

        mi_id.user_approver = user_id
       
        seq_no = mi_id.seq_no
        log_data = []

        try:
            for image in params.get('image_data'):
                new_image = self.env['material.inspection.images'].create({
                'image': image,
                'filename': str(fields.Datetime.now()),
                'mi_id':mi_id.id, })
                #image_ids.append(new_image.id)
        except Exception as e:
                _logger.info("---MI Imags--exception---------,%s",str(e))
                pass
        #_logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark')})
                
                # if send_notification:   
                #     if line.get('is_pass') == 'nop' :
                #         is_pass = 'na'
                #     else:
                #         is_pass = line.get('is_pass')

                    # logdata = {'role':'approver','user_id':user_id,'checklist_id':checklist_id.id,
                    # 'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_info_id.id,
                    # 'seq_no':seq_no,'remark':line.get('remark'),'status':'approve',
                    # 'overall_remark': overall_remark or mi_id.remark,'image':mi_id.image}
                    # log_data.append(logdata)

        if send_notification:
            # if log_data:
            #     child_records = [(0, 0, data) for data in log_data] 
            #     mi_id.write({'material_insp_log': child_records})
            mi_id.sudo().button_approve(seq_no,user_id)
        return



    def update_mi_checker(self,params):
        #_logger.info("---------update_mi_checker---------,%s", params)
        send_notification = False
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        
        user_id = int(params.get('user_id'))
        mi_id = self.browse(int(params.get('mi_id')))
        overall_remark = ''
        if params.get('overall_remark'):
            overall_remark = params.get('overall_remark')
            mi_id.write({'remark': overall_remark})

        if mi_id and user_id:
            mi_id.user_checker = user_id

        try:
            for image in params.get('image_data'):
                new_image = self.env['material.inspection.images'].create({
                'image': image,
                'filename': str(fields.Datetime.now()),
                'mi_id':mi_id.id, })
                #image_ids.append(new_image.id)
        except Exception as e:
                _logger.info("---MI Imags--exception---------,%s",str(e))
                pass
       
        seq_no = mi_id.seq_no
        log_data = []
        #_logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            
            for line in params.get('checklist_line'):
                checklist_id = self.env['material.inspection.line'].sudo().browse(int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write({'observation':line.get('is_pass'),'remark':line.get('remark')})
                
                # if send_notification:   
                #     if line.get('is_pass') == 'nop' :
                #         is_pass = 'na'
                #     else:
                #         is_pass = line.get('is_pass')

                    # logdata = {'role':'checker','user_id':user_id,'checklist_id':checklist_id.id,
                    # 'is_pass':is_pass,'mi_id':mi_id.id,'project_id':mi_id.project_info_id.id,
                    # 'seq_no':seq_no,'remark':line.get('remark'),'status':'checked',
                    # 'overall_remark': overall_remark or mi_id.remark,'image':mi_id.image}
                    # log_data.append(logdata)

        # if log_data:
        #     child_records = [(0, 0, data) for data in log_data] 
        #     mi_id.write({'material_insp_log': child_records})

        if send_notification:
            mi_id.sudo().button_checking_done(seq_no,user_id)
        return 

    
    def create_material_inspection(self,data):
        #_logger.info("----------create_material_inspection-------,%s",(data))

        send_notification = False
     
        if data.get('is_draft'):
            value = str(data.get('is_draft'))
            if value == 'no':
                send_notification = True
        project_info_id = int(data['project_info_id'])
        res = {
            "tower_id":int(data['tower_id']),
            #"title":data['title'],
            "project_info_id":project_info_id,
            "company_name": data['company_name'],
            "mir_no": data['mir_no'],
            "supplier_name": data['supplier_name'],
            "project_name": data['project_name'],
            "material_desc": data['material_description'],
            "invoice_no": data['invoice_no'],
            "quality_as_per_challan_inv": data['quantity_as_invoice'],
            "vehicle_no": data['vehicle_no'],
            "date_of_insp": data['date_of_inspection'],
            "date_of_material": data['date_of_material_received'],
            "batch_no": data['batch_no'],
            "remark": data['overall_remark'],
            "checked_by": int(data['check_by']),
            "image": data['image'] or '',
            "user_maker":int(data['check_by']),
            "status":'submit',
        }

        seq_no = self.env['material.inspection.seq'].get_or_create_seq_no(project_info_id)
        res.update({'seq_no':seq_no})    
        res_id = self.create(res)

        try:
            for image in data['image_data']:
                new_image = self.env['material.inspection.images'].create({
                'image': image,
                'filename': str(fields.Datetime.now()),
                'mi_id':res_id.id, })
                #image_ids.append(new_image.id)
        except Exception as e:
                _logger.info("---MI Imags--exception---------,%s",str(e))
                pass

        res = []
        log_data = []
        for line in data['checklist_data']:
            res.append({'material_insp':res_id.id,'checklist_id':line['mi_checklist_id'],'observation':line['is_pass'],'remark':line['remark']})
            # logdata = {'role':'maker','user_id':int(data['check_by']),'checklist_id':line['mi_checklist_id'],
            #         'is_pass':line['is_pass'],'mi_id':res_id.id,'project_id':res_id.project_info_id.id,
            #         'seq_no':seq_no,'remark':line['remark'],'status':res_id.status,
            #         'overall_remark': data['overall_remark']}
            # log_data.append(logdata)
        if res:
            self.env['material.inspection.line'].create(res)

        #mi_log = self.env['material.inspection.log'].create(log_data)
        # if log_data:
        #     child_records = [(0, 0, data) for data in log_data] 
        #     res_id.write({'material_insp_log': child_records})
        if send_notification:
            res_id.user_maker = int(data['check_by'])
            res_id.sudo().button_submit(seq_no,int(data['check_by']))
        return 

    # need to add mi by id
    def get_material_inspection(self,tower_id=False,mi_id=False):
        mi_data = []
        response = {}
        mi = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
  
        if tower_id:
            mi = self.search([('tower_id.id','=',int(tower_id))])
        if mi_id:
            mi = self.search([('id','=',int(mi_id))])
        if mi:
            for record in mi:
                #_logger.info("----------record-------,%s",(record))
                image=url+"/web/image?model=material.inspection&field=image&id="+str(record.id)

                
                data = {'id':record.id,'mi_status':record.mi_status or '','status':record.status,'seq_no':record.seq_no or '','project_info_id':record.project_info_id.id,'company_name':record.company_name,'image':image,
                                'tower_id':record.tower_id.id,'mir_no':record.mir_no,'supplier_name':record.supplier_name,
                                'material_desc':record.material_desc,'project_name':record.project_name,'invoice_no':record.invoice_no,
                                'quality_as_per_challan_inv':record.quality_as_per_challan_inv,'batch_no':record.batch_no,
                                'vehicle_no':record.vehicle_no,'date_of_insp':str(record.date_of_insp or ''),'date_of_material':str(record.date_of_material or ''),'remark':record.remark,
                                'checked_by':record.checked_by.id if record.checked_by else '','line_data':[]}
                if record.material_insp_line:
                    #_logger.info("-------record.material_insp_line------,%s",(record.material_insp_line))

                    line_data = []
                    for line in record.material_insp_line:
                        line_data.append({'id':line.id,'checklist_id':line.checklist_id.id,'observation':line.observation,'remark':line.remark})
                    data.update({'line_data':line_data})
                image_url_data = []
                try:
                    
                    for image_line in record.material_insp_img:
                        image=url+"/web/image?model=material.inspection.images&field=image&id="+str(image_line.id)
                        image_url_data.append(image)
                except Exception as e:
                        _logger.info("-get------MI Imags--exception---------,%s",str(e))
                        pass
                data.update({'image_url_data':image_url_data})
                mi_data.append(data)
                #_logger.info("-------mi_data------,%s",(mi_data))

        return mi_data

    # Update checklist maker sending to checker
    def button_submit(self,seq_no=None,user_id=None):
        #_logger.info("----------button submit---------,%s,%s,%s", self,seq_no,user_id)
        self.status='submit'
        self.mi_status='submit'
        
        group_name_not_found = 1
        notification_obj = self.env['app.notification']
        log_id = False
        sent = 0
        failed_log = {}
        failed_log.update({'seq_no':seq_no,'user_id':user_id,'method':'button_submit'})

        if user_id:
            player_id = ''
            message = ''
            #user , player_id  = self.env['res.users'].get_player_id(user_id)
            user_record = self.env['res.users'].browse(user_id)
            #user_groups = user_record.groups_id
            #_logger.info("------project_in fo---111-----,%s",self.project_info_id)
            #_logger.info("-----222-------,%s",self.project_info_id.assigned_to_ids)

            
            #self.get_users_data(user_record.name,'maker',seq_no,rec)
            if self.tower_id.assigned_to_ids:
                failed_log.update({'assigned_ids':self.tower_id.assigned_to_ids})
                #_logger.info("--button submit-----self.tower_id.assign_to_ids--------,%s",self.tower_id.assigned_to_ids)
                for user in self.tower_id.assigned_to_ids:
                    groups = user.groups_id
                    #_logger.info("---button submit-------groups submit---------,%s",groups)
                    for group in groups:
                        #_logger.info("------groupname----%s",group.name)
                        if str(group.name) == 'Checker':
                            group_name_not_found = 0
                            failed_log.update({'group_name':'checker'})
                            #_logger.info("----button submit-----checker- submitted--Maker-----")
                            player_id ,user_r = self.env['res.users'].get_player_id(user.id)
                            message = "CheckList No " +str(seq_no) + " Submitted by " + str(user_record.name)
                            #_logger.info("--button submit---1----message-player_id--------,%s,%s",message,player_id)
                            e = ''
                            if player_id and message and user:
                                try:
                                    title = str(user_record.name) + " Submitted the Checklist"
                                    log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'mi',self)
                                    sent = 1
                                except Exception as e:
                                    #_logger.info("----button submit---1---exception---------,%s",str(e))
                                    pass
                            else:
                                failed_log.update({'player_id':player_id,'message':message,'user':user,'error':str(e)})
                    if group_name_not_found:
                        failed_log.update({'group_name':'checker group name not found'})

            else:
                failed_log.update({'ids_not_found':'Assigned Ids Not Found'})

        if not sent and not log_id:
            self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})

    def button_set_to_maker(self,seq_no,user_id=False):
        #_logger.info("---button_set_to_maker------self,seq_no,user_id---------,%s,%s,%s",self,seq_no,user_id)

        self.status='draft'
        self.mi_status='checker_reject'

        notification_obj = self.env['app.notification']
        log_id = False
        sent = 0
        failed_log = {}
        group_name_not_found = 1
        failed_log.update({'seq_no':seq_no,'user_id':user_id,'method':'button_set_to_maker'})

        if user_id:
            player_id = ''
            message = ''
            #user , player_id  = self.env['res.users'].get_player_id(user_id)
            user_record = self.env['res.users'].browse(user_id)
            #user_groups = user_record.groups_id
            #self.get_users_data(user_record.name,'maker',seq_no,rec)
            #_logger.info("---button_set_to_maker-----self.user_maker-------,%s",self.user_maker)

            if not self.user_maker:
                if self.tower_id.assigned_to_ids:
                    failed_log.update({'assigned_ids':self.tower_id.assigned_to_ids})

                    #_logger.info("-- button_set_to_maker -----self.project_info_id.assign_to_ids--------,%s",self.project_info_id.assigned_to_ids)
                    for user in self.tower_id.assigned_to_ids:
                        groups = user.groups_id
                        #_logger.info("---button_set_to_maker-------groups ---------,%s",groups)
                        for group in groups:
                            #_logger.info("------groupname----%s",group.name)
                            if str(group.name) == 'Maker':
                                #_logger.info("----button_set_to_maker---------")
                                failed_log.update({'group_name':'maker'})
                                group_name_not_found = 0

                                player_id ,user_r = self.env['res.users'].get_player_id(user.id)
                                message = "CheckList No " +str(seq_no) + " Rejected by " + str(user_record.name)
                                #_logger.info("--button_set_to_maker---1----message-player_id--------,%s,%s",message,player_id)
                                e = ''
                                if player_id and message and user:
                                    try:
                                        title = str(user_record.name) + " Rejected the Checklist"
                                        log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'mi',self)
                                        sent = 1
                                    except Exception as e:
                                        #_logger.info("----button_set_to_maker---1---exception---------,%s",str(e))
                                        pass
                                else:
                                    failed_log.update({'player_id':player_id,'message':message,'user':user,'error':str(e)})
                        if group_name_not_found:
                            failed_log.update({'group_name':'maker group name not found'})
                else:
                    failed_log.update({'ids_not_found':'Assigned Ids Not Found'})

            else:
                player_id ,user_r = self.env['res.users'].get_player_id(self.user_maker.id)
                message = "CheckList No " +str(seq_no) + " Rejected by " + str(user_record.name)
                if player_id and message:
                    try:
                        title = str(user_record.name) + " Rejected the Checklist"
                        log_id = notification_obj.send_push_notification(title,[player_id],message,[self.user_maker.id],seq_no,'mi',self)
                        sent = 1
                    except Exception as e:
                        _logger.info("--MI--button_set_to_maker---1---exception---------,%s",str(e))
                        pass
                else:
                    failed_log.update({'player_id':player_id,'message':message,'user':user})

        if not sent and not log_id:
            self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})
        return True

    # update_checklist_checker sending to approver # Checker to approver
    def button_checking_done(self,seq_no=None,user_id=None):
        #_logger.info("----------button_checking_done-------,%s,%s", self,user_id)
        rec = self
        self.status='checked'
        self.mi_status='checked'

        notification_obj = self.env['app.notification']
        log_id = False
        sent = 0
        failed_log = {}
        group_name_not_found = 1
        failed_log.update({'seq_no':seq_no,'user_id':user_id,'method':'button_checking_done'})

        if user_id:
            player_id = ''
            message = ''
            #user , player_id  = self.env['res.users'].get_player_id(user_id)
            user_record = self.env['res.users'].browse(user_id)
            #user_groups = user_record.groups_id
            #self.get_users_data(user_record.name,'maker',seq_no,rec)
            if self.tower_id.assigned_to_ids:
                failed_log.update({'assigned_ids':self.tower_id.assigned_to_ids})
                #_logger.info("-- button_checking_done -----self.project_info_id.assign_to_ids--------,%s",self.project_info_id.assigned_to_ids)
                for user in self.tower_id.assigned_to_ids:
                    groups = user.groups_id
                    #_logger.info("---button_checking_done-------groups ---------,%s",groups)
                    for group in groups:
                        #_logger.info("------groupname----%s",group.name)
                        if str(group.name) == 'Approver':
                            group_name_not_found = 0
                            failed_log.update({'group_name':'approver'})

                            #_logger.info("----button_checking_done----checker to approver-----")
                            player_id ,user_r = self.env['res.users'].get_player_id(user.id)
                            message = "CheckList No " +str(seq_no) + " Submitted by " + str(user_record.name)
                            #_logger.info("--button_checking_done---1----message-player_id--------,%s,%s",message,player_id)
                            e = ''
                            if player_id and message and user:
                                try:
                                    title = str(user_record.name) + " Submitted the Checklist"
                                    log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'mi',self)
                                    sent = 1
                                except Exception as e:
                                    #_logger.info("----button_checking_done---1---exception---------,%s",str(e))
                                    pass
                            else:
                                failed_log.update({'player_id':player_id,'message':message,'user':user,'error':str(e)})

                    if group_name_not_found:
                        failed_log.update({'group_name':'approver group name not found'})
            else:
                failed_log.update({'ids_not_found':'Assigned Ids Not Found'})

        if not sent and not log_id:
            self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})
      
        self.checked_date = fields.Datetime.now()
        return True

    
    # update_checklist_approver Approver to custom admin
    def button_approve(self,seq_no=None,user_id=None):
        #_logger.info("----------button_approve-------,%s,%s,%s", self,seq_no,user_id)
        rec = self
        self.status='approve'
        self.mi_status='approve'

        notification_obj = self.env['app.notification']
        log_id = False
        group_name_not_found = 1
        sent = 0
        failed_log = {}
        failed_log.update({'seq_no':seq_no,'user_id':user_id,'method':'button_approve'})

        if user_id:
            player_id = ''
            message = ''
            #user , player_id  = self.env['res.users'].get_player_id(user_id)
            user_record = self.env['res.users'].browse(user_id)
            #user_groups = user_record.groups_id
            #self.get_users_data(user_record.name,'maker',seq_no,rec)
            if self.tower_id.assigned_to_ids:
                failed_log.update({'assigned_ids':self.tower_id.assigned_to_ids})

                #_logger.info("-- button_approve -----self.project_info_id.assign_to_ids--------,%s",self.project_info_id.assigned_to_ids)
                for user in self.tower_id.assigned_to_ids:
                    groups = user.groups_id
                    #_logger.info("---button_approve-------groups ---------,%s",groups)
                    for group in groups:
                        #_logger.info("------groupname----%s",group.name)
                        if str(group.name) == 'Custom Admin':
                            failed_log.update({'group_name':'Custom Admin'})
                            group_name_not_found = 0

                            #_logger.info("----button_approve----checker to approver-----")
                            player_id ,user_r = self.env['res.users'].get_player_id(user.id)
                            message = "CheckList No " +str(seq_no) + " Submitted by " + str(user_record.name)
                            #_logger.info("--button_approve---1----message-player_id--------,%s,%s",message,player_id)
                            e = ''
                            if player_id and message and user:
                                try:
                                    title = str(user_record.name) + " Submitted the Checklist"
                                    log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'mi',self)
                                    sent = 1
                                except Exception as e:
                                    _logger.info("----button_approve---1---exception---------,%s",str(e))
                                    pass
                            else:
                                failed_log.update({'player_id':player_id,'message':message,'user':user,'error':str(e)})
                    if group_name_not_found:
                        failed_log.update({'group_name':'custom admin group name not found'})
            else:
                failed_log.update({'ids_not_found':'Assigned Ids Not Found'})

        if not sent and not log_id:
            self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})
      
        self.approved_date = fields.Datetime.now()
        return True

    def button_set_to_checker(self,seq_no,user_id):
        #_logger.info("---button_set_to_checkers elf,seq_no,user_id---------,%s,%s,%s",self,seq_no,user_id)
        self.mi_status='approver_reject'
        self.status='submit'
        
        rec = self
        notification_obj = self.env['app.notification']
        log_id = False
        sent = 0
        failed_log = {}
        failed_log.update({'seq_no':seq_no,'user_id':user_id})
        group_name_not_found = 1

        if user_id:
            player_id = ''
            message = ''
            #user , player_id  = self.env['res.users'].get_player_id(user_id)
            user_record = self.env['res.users'].browse(user_id)
            #user_groups = user_record.groups_id
            #self.get_users_data(user_record.name,'maker',seq_no,rec)
            if not self.user_checker:

                if self.project_info_id.assigned_to_ids:
                    failed_log.update({'assigned_ids':self.project_info_id.assigned_to_ids})

                    #_logger.info("-- button_set_to_checker -----self.project_id.assign_to_ids--------,%s",self.project_info_id.assigned_to_ids)
                    for user in self.project_info_id.assigned_to_ids:
                        groups = user.groups_id
                        #_logger.info("---button_set_to_checker-------groups ---------,%s",groups)
                        for group in groups:
                            #_logger.info("------groupname----%s",group.name)
                            if str(group.name) == 'Checker':
                                failed_log.update({'group_name':'checker'})
                                group_name_not_found = 0

                                #_logger.info("----button_set_to_checker--------")
                                player_id ,user_r = self.env['res.users'].get_player_id(user.id)
                                message = "CheckList No " +str(seq_no) + " Rejected by " + str(user_record.name)
                                #_logger.info("--button_set_to_checker---1----message-player_id--------,%s,%s",message,player_id)
                                e = ''
                                if player_id and message and user:
                                    try:
                                        title = str(user_record.name) + " Rejected the Checklist"
                                        log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'mi',self)
                                        sent = 1
                                    except Exception as e:
                                        _logger.info("----button_set_to_checker---1---exception---------,%s",str(e))
                                        pass
                                else:
                                    failed_log.update({'player_id':player_id,'message':message,'user':user,'error':str(e)})
                        if group_name_not_found:
                            failed_log.update({'group_name':'checker group name not found'})
                else:
                    failed_log.update({'ids_not_found':'Assigned Ids Not Found'})

            else:
                player_id ,user_r = self.env['res.users'].get_player_id(self.user_checker.id)
                message = "CheckList No " +str(seq_no) + " Rejected by " + str(user_record.name)
                if player_id and message and user_record:
                    try:
                        title = str(user_record.name) + " Rejected the Checklist"
                        log_id = notification_obj.send_push_notification(title,[player_id],message,[self.user_checker.id],seq_no,'mi',self)
                        sent = 1
                    except Exception as e:
                        _logger.info("----button_set_to_chcker---1---exception---------,%s",str(e))
                        pass
                else:
                    failed_log.update({'player_id':player_id,'message':message,'user':user})
        if not sent and not log_id:
            self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})
        return 
        


class MaterialInspectionLine(models.Model):
    _name = 'material.inspection.line'
    _description = "MaterialInspectionLine"


    material_insp = fields.Many2one('material.inspection','Material Inspection')
    checklist_id = fields.Many2one('mi.checklist','Name')
    observation = fields.Selection(string='Observation',selection=[('yes', 'Yes'), ('no', 'No'),('na','Na')])
    remark = fields.Char('Remark')

class MaterialInspectionLog(models.Model):
    _name = 'material.inspection.log'
    _description = "MaterialInspectionLog"


    mi_id = fields.Many2one('material.inspection','Material Inspection')
    checklist_id = fields.Many2one('mi.checklist','Name')
    is_pass = fields.Selection([('yes', 'Yes'),('no', 'No'),('na', 'Not Applicable')],string="status")
    remark = fields.Char('Remark')
    overall_remarks = fields.Char('Overall Remark')
    title = fields.Text('Title')
    datetime = fields.Datetime('DateTime',default=lambda self: fields.Datetime.now())
    project_id = fields.Many2one("project.info",'Project')
    user_id = fields.Many2one('res.users','User')
    role = fields.Selection([('checker', 'Checker'),('maker', 'Maker'),('approver', 'Approver'),('manger', 'Manager'),('admin', 'Admin')],string="Role")
    seq_no = fields.Char("Seq No")
    url = fields.Char("URL")
    image = fields.Binary('Image')
    image_ids = fields.Many2many('ir.attachment', string='Images', domain=[('mimetype', 'ilike', 'image')])
    status=fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved')],default='draft',string="Status")


class MiChecklist(models.Model):
    _name = 'mi.checklist'
    _description = "MiChecklist"


    name = fields.Char(string='Name')


    def get_mi_checklist(self):
        checklist = self.search_read([], ['id', 'name'])
        return checklist

class MaterialInspectionSequence(models.Model):
    _name = 'material.inspection.seq'
    _rec_name = 'project_info_id'
    _description = "MaterialInspectionSequence"


    project_info_id = fields.Many2one('project.info','Project')
    current_month = fields.Char("Month")
    seq_no = fields.Char("Sequence No")

    def get_or_create_seq_no(self,project_id):
        
        current_month = datetime.now().strftime('%B')
        rec = self.search([('project_info_id','=',int(project_id)),('current_month','=',current_month)])
        
        if not rec:
            rec = self.create({'project_info_id':int(project_id),'current_month':current_month,'seq_no':'0001'})

        project_name = rec.project_info_id.name
        if not project_name:
            project_name = self.env['project.info'].browse(int(project_id)).name

        current_month = rec.current_month
        seq = rec.seq_no

        seq_no = project_name +"/"+ current_month +"/"+ seq
        int_value = int(seq)
        int_value += 1
        incremented_seq = f'{int_value:04}'
        rec.seq_no = str(incremented_seq)
        return seq_no

class MaterialInspectionImages(models.Model):
    _name = 'material.inspection.images'
    _order = 'id desc'
    _description = "MaterialInspectionImages"


    mi_id = fields.Many2one('material.inspection')
    #project_checklist_line_log_id = fields.Many2one('project.checklist.line.log')
    image = fields.Binary('File')
    filename = fields.Char("filename")




