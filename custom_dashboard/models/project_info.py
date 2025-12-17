# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta
from odoo import http
from odoo.http import request
import json
from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)
import base64



class TowerInspection(models.Model):
    _name = 'tower.inspection'
    _description = "TowerInspection"

    
    project_info_id = fields.Many2one('project.info','Project Id')
    name = fields.Char('Name')
    tower_id = fields.Many2one('project.tower','Tower')


class ProjectInfo(models.Model):
    _name = 'project.info'
    _description = "ProjectInfo"

    #_rec_name = 'name'

    name = fields.Char('Name')
    project_rating = fields.Float(string="Rating")
    bu_id = fields.Integer(string="Buid")
    image = fields.Binary("Image")
    assigned_to_ids = fields.Many2many('res.users')
    project_details_line = fields.One2many('project.details', 'project_info_id')
    tower_insp_line = fields.One2many('tower.inspection', 'project_info_id')
    project_info_tower_line = fields.One2many('project.tower', 'project_id')
    project_info_tower_line_temp = fields.One2many('project.info.tower.line.temp', 'project_id')
    lat = fields.Char('Latitude')
    longi = fields.Char('Longitude')
    visibility = fields.Boolean('Visibility',default=True)
    nc_count = fields.Integer(compute="_compute_total_flag_count_from_tower")
    yellow_flag_count = fields.Integer(compute="_compute_total_flag_count_from_tower")
    orange_flag_count = fields.Integer(compute="_compute_total_flag_count_from_tower")
    red_flag_count = fields.Integer(compute="_compute_total_flag_count_from_tower")
    green_flag_count = fields.Integer(compute="_compute_total_flag_count_from_tower")
    #project_progress_bar = fields.Float(string="Progress", compute="_compute_tower_progress_bar")
    project_progress_bar = fields.Float(string="Progress")

    activity_draft_count = fields.Integer(string='Draft Activities', compute='_compute_activity_counts')
    activity_submit_count = fields.Integer(string='Submit Activities', compute='_compute_activity_counts')
    activity_approved_count = fields.Integer(string='Approved Activities', compute='_compute_activity_counts')
    activity_checked_count = fields.Integer(string='Checker Activities', compute='_compute_activity_counts')

    maker_user_ids = fields.Many2many('res.users', 'maker_id', string='Maker', compute='_compute_maker_id')
    checker_user_ids = fields.Many2many('res.users', 'checker_id', string='Checker', compute='_compute_checker_id')
    approver_user_ids = fields.Many2many('res.users', 'approver_id', string='Approver', compute='_compute_approver_id')
    
    user_checker = fields.Many2one("res.users", string="Checker")
    user_approver = fields.Many2one("res.users", string="Approver")
    project_activity_id = fields.Many2one("project.activity.type")

    maker_pending_count = fields.Integer(string="Maker Pending Count", compute="_compute_c_m_a_counts", store=False)
    maker_completed_count = fields.Integer(string="Maker Completed Count", compute="_compute_c_m_a_counts", store=True)
    checker_pending_count = fields.Integer(string="Checker Pending Count", compute="_compute_c_m_a_counts", store=True)
    checker_completed_count = fields.Integer(string="Checker Completed Count", compute="_compute_c_m_a_counts", store=True)
    approver_pending_count = fields.Integer(string="Approver Pending Count", compute="_compute_c_m_a_counts", store=True)
    approver_completed_count = fields.Integer(string="Approver Completed Count", compute="_compute_c_m_a_counts", store=True)
    total_cma_pending = fields.Integer(compute="_compute_c_m_a_counts", store=True)
    total_cma_complete = fields.Integer(compute="_compute_c_m_a_counts", store=True)

    graph_data = fields.Text(string="Graph Data", compute="_compute_graph_data", store=False)
    project_list = fields.Text(string="Project List", compute="_compute_graph_data", store=False)

    def tower_name_list(self, project_id=False, tower=False):
        print(tower, 'tower---project_name_list\n\n\n-project id -----', project_id)
        # if project_id:
        #     projects = self.search([('project_info_tower_line', '=', project_id)])
        # else:
        if tower:
            towers = self.env['project.tower'].search([('id', '=', tower)])
        else:
            towers = self.search([])  # Retrieve all project records
        tower_list = []
        for tower in towers:
            tower_list.append(tower.name)
        return tower_list

    def project_name_list(self, project_id=False, tower=False):
        # if tower:
        #     projects = self.search([('project_info_tower_line', '=', project_id)])
        # else:
        if project_id:
            projects = self.search([('id', '=', project_id)])
        else:
            projects = self.search([])
        project_list = []
        for project in projects:
            project_list.append(project.name)
        return project_list

    @api.depends('project_activity_id')
    def _compute_graph_data(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            try:
                for record in self:
                    record.graph_data = ''
                    record.project_list = ''
                    graph_result, project_list = self.env['project.activity.type'].get_c_m_a_data(record.id, False)
                    record.graph_data = str(graph_result)
                    record.project_list = str(project_list)
            except Exception as e:
                    _logger.info("---_compute_graph_data---,%s",str(e))

    # @api.depends('graph_data', 'project_list')
    def _compute_c_m_a_counts(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                record.maker_pending_count = 0
                project_activity_info = self.env['project.activity.type'].sudo().search([('project_id', '=', record.id)])
                record.maker_pending_count = len(project_activity_info.filtered(lambda x: x.status=='draft').ids)
                record.maker_completed_count = len(project_activity_info.filtered(lambda x: x.status in ['submit','checked','approve']).ids)
                record.checker_pending_count = len(project_activity_info.filtered(lambda x: x.status in ['submit']).ids)
                record.checker_completed_count = len(project_activity_info.filtered(lambda x: x.status in ['checked','approve']).ids)
                record.approver_pending_count = len(project_activity_info.filtered(lambda x: x.status in ['checked']).ids)
                record.approver_completed_count = len(project_activity_info.filtered(lambda x: x.status in ['approve']).ids)

                record.total_cma_pending = (
                        record.maker_pending_count + record.checker_pending_count + record.approver_pending_count
                )
                record.total_cma_complete = (
                        record.maker_completed_count + record.checker_completed_count + record.approver_completed_count
                )

    def set_towers(self):
        # notifications= self.env['app.notification.log'].search([('status','=','sent')])
        # _logger.info("---notificationsnotifications--,%s",str(len(notifications)))
        # for notification in notifications:
        #     if notification.activity_type_id:
        #         _logger.info("---notificationsnotifications--,%s",str(len(notifications)))
        #         notification.checklist_status = notification.activity_type_id.status
        # _logger.info("------------Done-------,")
        # _logger.info("------------Done-------,")
        # _logger.info("------------Done-------,")
        # _logger.info("------------Done-------,")
        # return

        towers = []
        obj = self.env['project.info.tower.line.temp']
        if self.project_details_line:
            if self.project_details_line.tower_id:
                for tower in self.project_details_line.tower_id:
                    towers.append({'tower_id':tower.id,'name':tower.name,'project_id':self.id})
        if towers:
            if self.project_info_tower_line_temp:
                self.project_info_tower_line_temp.unlink()
            self.project_info_tower_line_temp.create(towers)
            #_logger.info("--towers---,%s",str(towers))
            # for tower in towers:
            #     rec = obj.search([('tower_id','=',tower['tower_id']),('project_id','=',tower['project_id'])])
            #     if not rec:
            #         obj.create(tower)
                
    @api.depends('assigned_to_ids')
    def _compute_maker_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                maker_ids = []
                maker_group = self.env['res.groups'].search([('name', '=', 'Maker')], limit=1)
                if record.assigned_to_ids:
                    for user in record.assigned_to_ids:
                        for group in user.groups_id:
                            if group.id == maker_group.id:
                                maker_ids.append(user.id)
                record.maker_user_ids = maker_ids

    @api.depends('assigned_to_ids')
    def _compute_checker_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                checker_ids = []
                checker_group = self.env['res.groups'].search([('name', '=', 'Checker')], limit=1)
                if record.assigned_to_ids:
                    for user in record.assigned_to_ids:
                        for group in user.groups_id:
                            if group.id == checker_group.id:
                                checker_ids.append(user.id)
                record.checker_user_ids = checker_ids

    @api.depends('assigned_to_ids')
    def _compute_approver_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                approver_ids = []
                approver_group = self.env['res.groups'].search([('name', '=', 'Approver')], limit=1)
                if record.assigned_to_ids:
                    for user in record.assigned_to_ids:
                        for group in user.groups_id:
                            if group.id == approver_group.id:
                                approver_ids.append(user.id)
                record.approver_user_ids = approver_ids

    @api.depends('project_info_tower_line.tower_floor_line_id.activity_ids')
    def _compute_activity_counts(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                draft_count = 0
                approved_count = 0
                submit_count = 0
                checked_count = 0
                for tower_line in record.project_info_tower_line:
                    for floors in tower_line.tower_floor_line_id:
                        for activity_id in floors.activity_ids:
                            for activity in activity_id.activity_type_ids:
                                if activity.status == 'draft':
                                    draft_count += 1
                                elif activity.status == 'submit':
                                    submit_count += 1
                                elif activity.status == 'checked':
                                    checked_count += 1
                                elif activity.status == 'approve':
                                    approved_count += 1
                record.activity_draft_count = draft_count
                record.activity_submit_count = submit_count
                record.activity_checked_count = checked_count
                record.activity_approved_count = approved_count

    @api.depends("project_info_tower_line_temp.project_nc", "project_info_tower_line_temp.project_yellow", "project_info_tower_line_temp.project_orange", "project_info_tower_line_temp.project_red", "project_info_tower_line_temp.project_green")
    def _compute_total_flag_count_from_tower(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                record.nc_count = 0
                record.yellow_flag_count = 0
                record.orange_flag_count = 0
                record.red_flag_count = 0
                record.green_flag_count = 0
                if record.project_info_tower_line_temp:
                    record.write({'nc_count': sum(record.project_info_tower_line_temp.mapped('project_nc')),
                    'yellow_flag_count': sum(record.project_info_tower_line_temp.mapped('project_yellow')),
                    'orange_flag_count': sum(record.project_info_tower_line_temp.mapped('project_orange')),
                    'red_flag_count': sum(record.project_info_tower_line_temp.mapped('project_red')),
                    'green_flag_count': sum(record.project_info_tower_line_temp.mapped('project_green'))
                    })


    def _compute_tower_progress_bar(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            try:
                for rec in self.search([('project_info_tower_line_temp', '!=', False)]):
                    rec.project_progress_bar = 0
                    if rec.project_info_tower_line:
                        #_logger.info("--------rec----,%s",str(rec))
                        tower_line = rec.project_info_tower_line
                        total_line = len(tower_line.filtered(lambda obj: obj.tower_progress_percentage != 0.0))
                        count_percent = sum(tower_line.mapped('tower_progress_percentage'))
                        total_percent = total_line * 100
                        if total_percent:  # Avoid division by zero
                            #_logger.info("--round((count_percent / total_percent) * 100, 2)---,%s",str(round((count_percent / total_percent) * 100, 2)))
                            rec.project_progress_bar = round((count_percent / total_percent) * 100, 2)

                    if rec.project_info_tower_line_temp:
                        #_logger.info("--------rec-2222---,%s",str(rec))
                        rec.project_info_tower_line_temp._compute_project_tower_progress_bar()
        
            except Exception as e:
                #rec.project_progress_bar = 0
                #_logger.info("Failed _compute_tower_progress_bar-----,%s",str(e))
                pass
    # def write(self, vals):
    #     res = super(ProjectInfo, self).write(vals)
    #     _logger.info("--write ----,%s,%s",vals,str(res))
    #     _logger.info("--------vals-----,%s",(vals))
    #     _logger.info("------res-----,%s",(res))
    #     print ("--valss--",vals)


    #     if self.project_details_line:
    #         tower_id_list = []
    #         for line in self.project_details_line:
    #             towers = self.project_info_tower_line_temp.mapped('tower_id')
    #             if line.tower_id:
    #                 for tower in line.tower_id:
    #                     if tower not in towers:
    #                         tower_id_list.append({'tower_id':tower.id,'name':tower.name,'project_id':self.id})
    #         self.project_info_tower_line_temp.create(tower_id_list)
    #     return res
    # def write(self, vals):
    #     res = super(ProjectInfo, self).write(vals)
    #     if self.project_details_line:
    #         tower_id_list = []
     
    #         for line in self.project_details_line:
    #             if line.tower_id:
    #                 for tower in line.tower_id:
    #                     tower_id_list.append({'tower_id':tower.id,'name':tower.name,'project_id':self.id})
            
    #         if self.project_info_tower_line_temp:
    #             self.project_info_tower_line_temp.unlink()
     
    #         self.project_info_tower_line_temp.create(tower_id_list)
    #     return res


    # def get_project_tower_nc_data(self,project_id,tower_id):
    #     projects = self.env['project.info'].search([('id','=',project_id)])
    #     for pro in projects:
    #         #project = {'project_name':pro.name,'project_id':pro.id,'nc_count':pro.nc_count,'yellow_flag_count':pro.yellow_flag_count,'orange_flag_count':pro.orange_flag_count,'red_flag_count':pro.red_flag_count,'green_flag_count':pro.green_flag_count}
    #         tower_lst = {}
    #         pr_rec = self.env['project.info.tower.line.temp'].search([('project_id','=',project_id),('tower_id','=',tower_id)])
    #         for line in pro.project_info_tower_line_temp:
    #             if line.tower_id.id == tower_id:
    #                 tower_lst = {'tower_name':line.tower_id.name,'tower_id':line.tower_id.id,'project_nc':line.project_nc,'project_yellow':line.project_yellow,'project_orange':line.project_orange,'project_red':line.project_red,'green_flag_count':line.project_green}
    #                 floor_lst = []
    #                 for floor_line in line.tower_id.tower_floor_line_id:
    #                     floor_lst.append({'floor_name':floor_line.project_floor_id.name,'floor_id':floor_line.project_floor_id.id})
    #                 tower_lst['floor_data'] = floor_lst
    #     return tower_lst

    #/get/project/nc
    def get_project_nc_data(self,project_id):
        projects = self.env['project.info'].search([('id','=',project_id)])
        for pro in projects:
            project = {'project_name':pro.name,'project_id':pro.id,'nc_count':pro.nc_count,'yellow_flag_count':pro.yellow_flag_count,'orange_flag_count':pro.orange_flag_count,'red_flag_count':pro.red_flag_count,'green_flag_count':pro.green_flag_count}
            a = 0
            tower_lst = []
            for line in pro.project_info_tower_line_temp:
                #tower_lst.append({'tower_name':line.tower_id.name,'tower_id':line.tower_id.id,'project_nc':line.project_nc,'project_yellow':line.project_yellow,'project_orange':line.project_orange,'project_red':line.project_red,'green_flag_count':line.project_green})
                if line.tower_id:
                    tower_lst.append({'tower_name':line.tower_id.name,'tower_id':line.tower_id.id})
            project['tower_data'] = tower_lst
        return project

    #/get/project/tower/nc
    def get_project_tower_nc_data(self,project_id,tower_id):
        projects = self.env['project.info'].search([('id','=',project_id)])
        for pro in projects:
            #project = {'project_name':pro.name,'project_id':pro.id,'nc_count':pro.nc_count,'yellow_flag_count':pro.yellow_flag_count,'orange_flag_count':pro.orange_flag_count,'red_flag_count':pro.red_flag_count,'green_flag_count':pro.green_flag_count}
            tower_lst = {}
            pr_rec = self.env['project.info.tower.line.temp'].search([('project_id','=',project_id),('tower_id','=',tower_id)])
            if pr_rec:
                line = pr_rec

                tower_lst = {'tower_name':line.tower_id.name,'tower_id':line.tower_id.id,'project_nc':line.project_nc,'project_yellow':line.project_yellow,'project_orange':line.project_orange,'project_red':line.project_red,'green_flag_count':line.project_green}
                floor_lst = []
                for floor_line in line.tower_id.tower_floor_line_id:
                    floor_lst.append({'floor_name':floor_line.project_floor_id.name,'floor_id':floor_line.project_floor_id.id})
                tower_lst['floor_data'] = floor_lst

                flat_lst = []
                for flat_line in line.tower_id.tower_flat_line_id:
                    flat_lst.append({'flat_name':flat_line.project_flat_id.name,'flat_id':flat_line.project_flat_id.id})
                tower_lst['flat_data'] = flat_lst

        return tower_lst

    #/get/tower/floor/nc
    def get_project_tower_floor_nc_data(self,project_id,tower_id,floor_id):

        floor = self.env['project.floors'].search([('id','=',floor_id),('tower_id','=',tower_id),('project_id','=',project_id)])
        data = []
        if floor:
            data = {'name':floor.name,'id':floor.id,'nc':floor.floors_nc,'floors_yellow':floor.floors_yellow,'floors_orange':floor.floors_orange,'floors_red':floor.floors_red,'floors_green':floor.floors_green}
            activity_data = []
            for activity in floor.activity_ids:
                activity_data.append({'activity_name':activity.project_activity_id.name,'activity_id':activity.project_activity_id.id})
            data['activity_data'] = activity_data
        return data

    #/get/floor/activity/nc
    def get_floor_activity_nc(self,project_id,tower_id,floor_id,activity_id):
        activity_rec = self.env['project.activity'].search([('id','=',activity_id),('floor_id','=',floor_id),('tower_id','=',tower_id),('project_id','=',project_id)])
        data = {}
        if activity_rec:
            data = {'activity_name':activity_rec.name,'activity_id':activity_rec.id,'act_nc':activity_rec.act_nc,'act_yellow':activity_rec.act_yellow,'act_orange':activity_rec.act_orange,'act_red':activity_rec.act_red,'act_green':activity_rec.act_green}
            type_data = []
            for act_type in activity_rec.activity_type_ids:
                type_data.append({'activity_type_name':act_type.name,'activity_type_id':act_type.id})
            data['activity_type'] = type_data
        return data

    #/get/floor/activity_type/nc
    def get_floor_activity_type_nc(self,activity_id,type_id):
        #_logger.info("----get_floor_activity_type_nc-------,%s,%s",(activity_id,type_id))

        activity_type_rec = self.env['project.activity.type'].search([('id','=',type_id),('activity_id','=',activity_id)])
        data = {}
        if activity_type_rec:
            data = {'activity_type_name':activity_type_rec.name,'activity_type_id':activity_type_rec.id,'act_type_nc':activity_type_rec.act_type_nc,'act_type_yellow':activity_type_rec.act_type_yellow,'act_type_orange':activity_type_rec.act_type_orange,'act_type_red':activity_type_rec.act_type_red,'act_type_green':activity_type_rec.act_type_green}
            ck_data = []
            for ckl in activity_type_rec.checklist_ids:
                ck_data.append({'checklist_name':ckl.checklist_template_id.name,'checklist_id':ckl.id})
            data['checklist'] = ck_data
        #_logger.info("----get_floor_activity_type_nc----data---,%s",(data))

        return data

    #/get/floor/checklist/nc
    def get_floor_checklist_nc(self,checklist_id):
        ckl = self.env['project.checklist.line'].search([('id','=',checklist_id)])
        data = {}
        if ckl:
            data = {'checklist_name':ckl.checklist_template_id.name,'checklist_id':ckl.id,'project_line_nc':ckl.project_line_nc,'project_line_yellow':ckl.project_line_yellow,'project_line_orange':ckl.project_line_orange,'project_line_red':ckl.project_line_red}
        return data

    ### For Flats ###

    def get_project_towerflat_nc_data(self,project_id,tower_id):
        projects = self.env['project.info'].search([('id','=',project_id)])
        for pro in projects:
            #project = {'project_name':pro.name,'project_id':pro.id,'nc_count':pro.nc_count,'yellow_flag_count':pro.yellow_flag_count,'orange_flag_count':pro.orange_flag_count,'red_flag_count':pro.red_flag_count,'green_flag_count':pro.green_flag_count}
            tower_lst = {}
            pr_rec = self.env['project.info.tower.line.temp'].search([('project_id','=',project_id),('tower_id','=',tower_id)])
            if pr_rec:
                line = pr_rec
                tower_lst = {'tower_name':line.tower_id.name,'tower_id':line.tower_id.id,'project_nc':line.project_nc,'project_yellow':line.project_yellow,'project_orange':line.project_orange,'project_red':line.project_red,'green_flag_count':line.project_green}
                flat_lst = []
                for flat_line in line.tower_id.tower_flat_line_id:
                    flat_lst.append({'flat_name':flat_line.project_flat_id.name,'flat_id':flat_line.project_flat_id.id})
                tower_lst['flat_data'] = flat_lst
        return tower_lst


    def get_project_tower_flat_nc_data(self,project_id,tower_id,flat_id):

        flat = self.env['project.flats'].search([('id','=',flat_id),('tower_id','=',tower_id),('project_id','=',project_id)])
        data = []
        if flat:
            data = {'name':flat.name,'id':flat.id,'nc':flat.flats_nc,'flats_yellow':flat.flats_yellow,'flats_orange':flat.flats_orange,'flats_red':flat.flats_red,'flats_green':flat.flats_green}
            activity_data = []
            for activity in flat.activity_ids:
                activity_data.append({'activity_name':activity.project_activity_id.name,'activity_id':activity.project_activity_id.id})
            data['activity_data'] = activity_data
        return data

    def get_flat_activity_nc(self,project_id,tower_id,flat_id,activity_id):
        activity_rec = self.env['project.activity'].search([('id','=',activity_id),('flat_id','=',flat_id),('tower_id','=',tower_id),('project_id','=',project_id)])
        data = {}
        if activity_rec:
            data = {'activity_name':activity_rec.name,'activity_id':activity_rec.id,'act_nc':activity_rec.act_nc,'act_yellow':activity_rec.act_yellow,'act_orange':activity_rec.act_orange,'act_red':activity_rec.act_red,'act_green':activity_rec.act_green}
            type_data = []
            for act_type in activity_rec.activity_type_ids:
                type_data.append({'activity_type_name':act_type.name,'activity_type_id':act_type.id})
            data['activity_type'] = type_data
        return data


    def get_flat_activity_type_nc(self,type_id,activity_id):
        activity_type_rec = self.env['project.activity.type'].search([('id','=',type_id),('activity_id','=',activity_id)])
        data = {}
        if activity_type_rec:
            data = {'activity_type_name':activity_type_rec.name,'activity_type_id':activity_type_rec.id,'act_type_nc':activity_type_rec.act_type_nc,'act_type_yellow':activity_type_rec.act_type_yellow,'act_type_orange':activity_type_rec.act_type_orange,'act_type_red':activity_type_rec.act_type_red,'act_type_green':activity_type_rec.act_type_green}
            ck_data = []
            for ckl in activity_type_rec.checklist_ids:
                ck_data.append({'checklist_name':ckl.checklist_template_id.name,'checklist_id':ckl.id})
            data['checklist'] = ck_data
        return data


    def get_flat_checklist_nc(self,checklist_id):
        #_logger.info("----get_floor_activity_type_nc----ckl---,%s",(checklist_id))

        ckl = self.env['project.checklist.line'].search([('id','=',checklist_id)])
        #_logger.info("----get_floor_activity_type_nc----ckl---,%s",(ckl))

        data = {}
        if ckl:
            data = {'checklist_name':ckl.checklist_template_id.name,'checklist_id':ckl.id,'project_line_nc':ckl.project_line_nc,'project_line_yellow':ckl.project_line_yellow,'project_line_orange':ckl.project_line_orange,'project_line_red':ckl.project_line_red}
        return data



    ### For Flats End ##



    # def get_project_tower_floor_nc_data(self,project_id,tower_id,floor_id):
    #     projects = self.env['project.info'].search([('id','=',project_id)])
    #     for pro in projects:
    #         #project = {'project_name':pro.name,'project_id':pro.id,'nc_count':pro.nc_count,'yellow_flag_count':pro.yellow_flag_count,'orange_flag_count':pro.orange_flag_count,'red_flag_count':pro.red_flag_count,'green_flag_count':pro.green_flag_count}
    #         floor_lst = []
    #         for line in pro.project_info_tower_line_temp:
    #             if line.tower_id.id == tower_id:
    #                 #tower_lst.append({'tower_name':line.tower_id.name,'tower_id':line.tower_id.id,'project_nc':line.project_nc,'project_yellow':line.project_yellow,'project_orange':line.project_orange,'project_red':line.project_red,'green_flag_count':line.project_green})
    #                 for floor_line in line.tower_id.tower_floor_line_id:
    #                     if floor_line.project_floor_id.id == floor_id:
    #                         floor_lst.append({'floor_name':floor_line.project_floor_id.name,'floor_id':floor_line.project_floor_id.id,'floor_nc':floor_line.floors_nc,'floors_yellow':floor_line.floors_yellow,'floors_orange':floor_line.floors_orange,'floors_red':floor_line.floors_red,'floors_green':floor_line.floors_green})

    #     return floor_lst


    def get_nc_data(self,project_id):
        projects = self.env['project.info'].search([('id','=',project_id)])
        for pro in projects:
            project = {'project_name':pro.name,'project_id':pro.id,'nc_count':pro.nc_count,'yellow_flag_count':pro.yellow_flag_count,'orange_flag_count':pro.orange_flag_count,'red_flag_count':pro.red_flag_count,'green_flag_count':pro.green_flag_count}
            a = 0
            tower_lst = []
            for line in pro.project_info_tower_line_temp:
                if line.tower_id:
                    tower_lst.append({'tower_name':line.tower_id.name,'tower_id':line.tower_id.id,'project_nc':line.project_nc,'project_yellow':line.project_yellow,'project_orange':line.project_orange,'project_red':line.project_red,'green_flag_count':line.project_green})
                    x = 0
                    floor_lst = []
                    for floor_line in line.tower_id.tower_floor_line_id:
                        floor_lst.append({'floor_name':floor_line.project_floor_id.name,'floor_id':floor_line.project_floor_id.id,'floor_nc':floor_line.floors_nc,'floors_yellow':floor_line.floors_yellow,'floors_orange':floor_line.floors_orange,'floors_red':floor_line.floors_red,'floors_green':floor_line.floors_green})
                        y = 0
                        activity_lst = []
                        for activity_line in floor_line.activity_ids:
                            activity_lst.append({'activity_name':activity_line.project_activity_id.name,'activity_id':activity_line.project_activity_id.id,'act_nc':activity_line.act_nc,'act_yellow':activity_line.act_yellow,'act_orange':activity_line.act_orange,'act_red':activity_line.act_red,'act_green':activity_line.act_green})
                            #activity_lst.append(activity)
                            z = 0
                            activity_type = []
                            for at_line in activity_line.activity_type_ids:
                                activity_type.append({'activity_type_name':at_line.project_actn_id.name,'activity_type_id':at_line.project_actn_id.id,'act_type_nc':at_line.act_type_nc,'act_type_yellow':at_line.act_type_yellow,'act_type_orange':at_line.act_type_orange,'act_type_red':at_line.act_type_red,'act_type_green':at_line.act_type_green})

                                checklist_data = []
                                for ckl in at_line.checklist_ids:
                                    checklist_data.append({'checklist_name':ckl.checklist_template_id.name,'checklist_id':ckl.checklist_template_id.id,'project_line_nc':ckl.project_line_nc,'project_line_yellow':ckl.project_line_yellow,'project_line_orange':ckl.project_line_orange,'project_line_red':ckl.project_line_red})
                                    #print ("--checklist--",checklist)
                                    #checklist_data.apend(checklist)
                                activity_type[z]['checkist_ncs'] = checklist_data
                                z+=1
                            activity_lst[y]['type_ncs'] = activity_type
                            y+=1
                        floor_lst[x]['activity_nc'] = activity_lst
                        x+=1

                    flat_lst = []
                    b = 0
                    for flat_line in line.tower_id.tower_flat_line_id:
                        flat_lst.append({'flat_name':flat_line.project_flat_id.name,'flat_id':flat_line.project_flat_id.id,'flats_nc':flat_line.flats_nc,'flats_yellow':flat_line.flats_yellow,'flats_orange':flat_line.flats_orange,'flats_red':flat_line.flats_red,'flats_green':flat_line.flats_green})
                        activity_lst = []
                        c = 0
                        for activity_line in flat_line.activity_ids:
                            activity_lst.append({'activity_name':activity_line.project_activity_id.name,'activity_id':activity_line.project_activity_id.id,'act_nc':activity_line.act_nc,'act_yellow':activity_line.act_yellow,'act_orange':activity_line.act_orange,'act_red':activity_line.act_red,'act_green':activity_line.act_green})
                            activity_type_lst = []
                            d=0
                            for at_line in activity_line.activity_type_ids:
                                activity_type_lst.append({'activity_type_name':at_line.project_actn_id.name,'activity_type_id':at_line.project_actn_id.id,'act_type_nc':at_line.act_type_nc,'act_type_yellow':at_line.act_type_yellow,'act_type_orange':at_line.act_type_orange,'act_type_red':at_line.act_type_red,'act_type_green':at_line.act_type_green})
                                checklist_lst = []
                                for ckl in at_line.checklist_ids:
                                    checklist_lst.append({'checklist_name':ckl.checklist_template_id.name,'checklist_id':ckl.checklist_template_id.id,'project_line_nc':ckl.project_line_nc,'project_line_yellow':ckl.project_line_yellow,'project_line_orange':ckl.project_line_orange,'project_line_red':ckl.project_line_red})
                                    #print ("--checklist--",checklist)
                                activity_type_lst[d]['checkist_ncs'] = checklist_lst
                                d+=1
                            activity_lst[c]['type_ncs'] = activity_type_lst
                            c+=1
                        flat_lst[b]['activity_nc'] = activity_lst
                        b+=1

                    tower_lst[a]['flat_nc'] = flat_lst
                    tower_lst[a]['floor_nc'] = floor_lst
                    a+=1

            project['tower_floor_flat_nc'] =  tower_lst
        #_logger.info("----project-------,%s",(project))


        return project

    # def generate_seq_floors(self):
    #     if self.project_info_tower_line_temp:
    #         for building in self.project_info_tower_line_temp:
    #             if building.tower_id:
    #                 building_name = building.name

    #                 for floor in building.tower_id.tower_floor_line_id:
    #                     floor_name = floor.name
    #                     activity_seq = '001'
    #                     for activity in floor.activity_ids:
    #                         #_logger.info("-------activity.name-------,%s",(activity.name))
    #                         if activity.name:
    #                             #activity_name = activity.name[:4].strip()
    #                             activity_name = activity.name

    #                             activity.index_no = activity_seq
    #                             new_number = int(activity_seq) + 1
    #                             activity_seq = '{:03d}'.format(new_number)
    #                             activity_type_seq = '001'
    #                             for activity_type in activity.activity_type_ids:
    #                                 no = 1 + 1
    #                                 temp = activity_type_seq
    #                                 activity_type.index_no = activity_type_seq
    #                                 new_number = int(activity_type_seq) + 1
    #                                 activity_type_seq = '{:03d}'.format(new_number)
    #                                 activity_type.seq_no = "VJD"+"/"+ str(self.name) +"/" + str(building_name) + "/" + str(floor_name) +"/" + str(activity_name) + "/" + str(temp)


    # def generate_seq_flats(self):
    #     if self.project_info_tower_line_temp:
    #         for building in self.project_info_tower_line_temp:
    #             #_logger.info("-------building.name------,%s",(building.name))
    #             building_name = building.name
    #             for flat in building.tower_id.tower_flat_line_id:
    #                 flat_name = flat.name
    #                 activity_seq = '001'
    #                 for activity in flat.activity_ids:
    #                     #_logger.info("-------activity.name-------,%s",(activity.name))
    #                     if activity.name:
    #                         #activity_name = activity.name[:4].strip()
    #                         activity_name = activity.name

    #                         activity.index_no = activity_seq
    #                         new_number = int(activity_seq) + 1
    #                         #activity_seq = '{:03d}'.format(new_number)
    #                         activity_type_seq = '001'
    #                         for activity_type in activity.activity_type_ids:
    #                             no = 1 + 1
    #                             temp = activity_type_seq
    #                             activity_type.index_no = activity_type_seq
    #                             new_number = int(activity_type_seq) + 1
    #                             activity_type_seq = '{:03d}'.format(new_number)
    #                             activity_type.seq_no = "VJD"+"/"+ str(self.name) +"/" + str(building_name) + "/" + str(flat_name) +"/" + str(activity_name) + "/" + str(temp)
    #                             #print ("--activity_type.seq_no--",activity_type.seq_no)


    def get_all_projects_details(self,user_id):
        #_logger.info("-------get_all_projects_details--------,%s,%s",(user_id,self.env.user.id))

        master_project_data = []
        response = {}
        projects = self.search([('assigned_to_ids','in',self.env.user.id)])
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        if projects:
            for project in projects:
                project_data = {}
                master_checklist_data= []
                base_url=url+"/web/image?model=project.info&field=image&id="+str(project.id)
                project_data = {"name":project.name,"image":base_url,"project_id":project.id}
                if project.project_details_line:
                    for line in project.project_details_line:
                        image=url+"/web/image?model=project.details&field=image&id="+str(line.id)
                        line_data = {'name':line.name,'image':image,'checklist_id':line.id}
                        master_checklist_data.append(line_data)
                project_data['checklist_data'] = master_checklist_data
                master_project_data.append(project_data)
        #_logger.info("---------master_project_data--------,%s",len(master_project_data))
        return master_project_data

    def get_all_projects_towers_checklist_details(self,user_id):
        #_logger.info("-------get_all_projects_towers_checklist_details--------,%s,%s",(user_id,self.env.user.id))

        master_project_data = []
        response = {}
        projects = self.search([('assigned_to_ids','in',self.env.user.id)])
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')

        if projects:
            for project in projects:
                project_data = {}
                checklist_data= []
                tower_data = []
                base_url=url+"/web/image?model=project.info&field=image&id="+str(project.id)
                project_data = {"name":project.name,"image":base_url,"project_id":project.id}
                if project.project_details_line:
                    for line in project.project_details_line:
                        image=url+"/web/image?model=project.details&field=image&id="+str(line.id)
                        line_data = {'name':line.name,'image':image,'checklist_id':line.id}
                        checklist_data.append(line_data)
                project_data['checklist_data'] = checklist_data
                if project.project_info_tower_line_temp:
                    for line in project.project_info_tower_line_temp:
                        line_data = {}
                        line_data = {'name':line.tower_id.name,'tower_id':line.tower_id.id}
                        tower_data.append(line_data)
                project_data['tower_data'] = tower_data

                master_project_data.append(project_data)
        #_logger.info("---------master_project_data--------,%s",len(master_project_data))

        return master_project_data


    def get_all_projects_all_flats_floors_details(self,user_id):
        #_logger.info("-------get_all_projects_all_flats_floors_details--------,%s,%s",(user_id,self.env.user.id))

        master_project_data = []
        response = {}
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        projects = self.search([('assigned_to_ids','in',self.env.user.id)])

        #print ("--projects--",projects)
        if projects:
            project_info = []
            pdata = 0
            for project in projects:
                base_url=url+"/web/image?model=project.info&field=image&id="+str(project.id)
                #project_data.append({"name":project.name,"image":base_url,"project_id":project.id,"detail_lines":''})
                project_data = {"name":project.name,"image":base_url,"project_id":project.id,"detail_lines":''}
                line_data = []
                ydx = 0
                # if project.project_details_line:
                qdx = 0
                for line in project.project_details_line:
                    image=url+"/web/image?model=project.details&field=image&id="+str(line.id)
                    line_data.append({'name':line.name,'image':image,'line_id':line.id})
                    #master_data.append(line_data)
                    building_data = []
                    pdx = 0
                    pdx_f = 0
                    for building in line.tower_id:
                        building_data.append({'name':building.name,'id':building.id})
                        tower_data = []
                        odx = 0
                        for floor in building.tower_floor_line_id:
                            tower_data.append({'line_id':floor.id,'name':floor.name,'id':floor.project_floor_id.id,'flor_no':floor.floor_id})
                            activity_data = []
                            jdx = 0
                            for activity in floor.activity_ids:
                                activity_data.append({'id':activity.project_activity_id.id,'name':activity.name,'line_id':activity.id,'description':activity.description or '','write_date':str(activity.write_date)})
                                type_data = []
                                idx = 0
                                for type in activity.activity_type_ids:
                                    activity_status = type.status
                                    if type.status == 'approver_reject':
                                        activity_status='submit'
                                    if type.status == 'checker_reject':
                                        activity_status='draft'
                                    type_data.append({'id':type.project_actn_id.id,'name':type.name,'line_id':type.id,'activity_status':activity_status,'activity_type_progress':type.progress_percentage})

                                    checklist_data = []
                                    for checklist in type.checklist_ids:
                                        # for line in checklist.image_ids:
                                        #     image_datas = []
                                        #     image_base64 = base64.b64encode(line.image).decode('utf-8')
                                        #     image_datas.append(image_base64)
                                        #checklist_data.append({'id':checklist.id,'checklist_template_id':checklist.checklist_template_id.id,'checklist_template_name':checklist.checklist_template_id.name,'reason':checklist.reason,'project_line_nc':checklist.project_line_nc,'project_line_yellow':checklist.project_line_yellow,'project_line_orange':checklist.project_line_orange,'project_line_red':checklist.project_line_red,'project_line_cre_date':str(checklist.project_line_cre_date),'is_pass':checklist.is_pass})
                                        checklist_data.append({'line_id':checklist.id,'id':checklist.checklist_template_id.id,'checklist_template_name':checklist.checklist_template_id.name,'reason':checklist.reason,'project_line_nc':checklist.project_line_nc,'project_line_yellow':checklist.project_line_yellow,'project_line_orange':checklist.project_line_orange,'project_line_red':checklist.project_line_red,'project_line_cre_date':str(checklist.project_line_cre_date),'is_pass':checklist.is_pass})
                                    type_data[idx]['check_templates'] = checklist_data
                                    idx+=1
                                activity_data[jdx]['type_details'] = type_data
                                jdx+=1
                            tower_data[odx]['activity_details'] = activity_data
                            odx+=1

                        odx_f = 0
                        tower_data_f = []
                        for flat in building.tower_flat_line_id:
                            tower_data_f.append({'id':flat.project_flat_id.id,'name':flat.name,'line_id':flat.id,'flat_no':flat.flat_id,'floor_id':flat.floor_id.id or ''})
                            #{'name':floor.project_floor_id.name,'id':floor.id,'flor_no':floor.floor_id}
                            activity_data_f = []
                            jdx_f = 0
                            for activity in flat.activity_ids:
                                activity_data_f.append({'id':activity.project_activity_id.id,'name':activity.name,'line_id':activity.id,'description':activity.description or '','write_date':str(activity.write_date)})
                                type_data_f = []
                                idx_f = 0
                                for type in activity.activity_type_ids:
                                    activity_status = type.status
                                    if type.status == 'approver_reject':
                                        activity_status='submit'
                                    if type.status == 'checker_reject':
                                        activity_status='draft'
                                    #type_data_f.append({'name':type.name})
                                    type_data_f.append({'id':type.project_actn_id.id,'name':type.name,'line_id':type.id,'activity_status':activity_status,'activity_type_progress':type.progress_percentage})

                                    checklist_data_f = []
                                    for checklist in type.checklist_ids:
                                        image_datas = []
                                        #checklist_data_f.append({'id':checklist.checklist_template_id.name})
                                        # for line in checklist.image_ids:
                                        #     #real_photo = meeting.real_photo.decode('utf-8')

                                        #     image_base64 = base64.b64encode(line.image).decode('utf-8')
                                        #     image_datas.append(image_base64)
                                        checklist_data_f.append({'line_id':checklist.id,'id':checklist.checklist_template_id.id,'checklist_template_name':checklist.checklist_template_id.name,'reason':checklist.reason,'project_line_nc':checklist.project_line_nc,'project_line_yellow':checklist.project_line_yellow,'project_line_orange':checklist.project_line_orange,'project_line_red':checklist.project_line_red,'project_line_cre_date':str(checklist.project_line_cre_date),'is_pass':checklist.is_pass})

                                    type_data_f[idx_f]['check_templates'] = checklist_data_f
                                    idx_f+=1
                                activity_data_f[jdx_f]['type_details'] = type_data_f
                                jdx_f+=1

                            tower_data_f[odx_f]['activity_details'] = activity_data_f
                            odx_f+=1
                        building_data[pdx]['foor_details'] = tower_data
                        building_data[pdx_f]['flat_details'] = tower_data_f
                        pdx+=1
                        pdx_f+=1

                    line_data[qdx]['tower_details'] = building_data
                    qdx+=1

                project_data['detail_lines'] = line_data
                master_project_data.append(project_data)
        #print ("--master_project_data--",master_project_data)
        #_logger.info("---------master_project_data--------,%s",len(master_project_data))

        return master_project_data

class ProjectInfoTower(models.Model):
    _name = 'project.info.tower'
    _description = "ProjectInfoTower"


    project_tower_id = fields.Many2one('project.info')
    project_info_tower_id = fields.Many2one('project.tower',string='Project Info Tower')

class ProjectInfoTowerLineTemp(models.Model):
    _name = 'project.info.tower.line.temp'
    _description = "ProjectInfoTowerLineTemp"


    project_id = fields.Many2one('project.info','ProjectInfo')
    name = fields.Char('Name')
    tower_id = fields.Many2one('project.tower',string="Tower")

    project_nc = fields.Integer('NC', compute='_compute_total_flag_count_from_tower')
    project_red = fields.Integer('Red Flag', compute='_compute_total_flag_count_from_tower')
    project_orange = fields.Integer('Orange Flag', compute='_compute_total_flag_count_from_tower')
    project_yellow = fields.Integer('Yellow Flag', compute='_compute_total_flag_count_from_tower')
    project_green = fields.Integer('Green Flag', compute='_compute_total_flag_count_from_tower')
    project_tower_progress = fields.Float(string="Progress")


    @api.depends('tower_id.tower_flat_line_id.flats_nc', 'tower_id.tower_flat_line_id.flats_orange', 'tower_id.tower_flat_line_id.flats_orange',
    'tower_id.tower_flat_line_id.flats_red', 'tower_id.tower_flat_line_id.flats_green', 'tower_id.tower_floor_line_id.floors_nc', 'tower_id.tower_floor_line_id.floors_orange', 'tower_id.tower_floor_line_id.floors_yellow', 'tower_id.tower_floor_line_id.floors_red', 'tower_id.tower_floor_line_id.floors_green')
    def _compute_total_flag_count_from_tower(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:

            for record in self:
                record.project_nc = 0
                record.project_red = 0
                record.project_yellow = 0
                record.project_orange = 0
                record.project_green = 0
                # return
                if record.tower_id.tower_flat_line_id or  record.tower_id.tower_floor_line_id  :
                    record.project_nc = sum(record.tower_id.tower_flat_line_id.mapped('flats_nc')) + sum(record.tower_id.tower_floor_line_id.mapped('floors_nc'))
                    record.project_yellow = sum(record.tower_id.tower_flat_line_id.mapped('flats_yellow')) +  sum(record.tower_id.tower_floor_line_id.mapped('floors_yellow'))
                    record.project_orange = sum(record.tower_id.tower_flat_line_id.mapped('flats_orange')) +  sum(record.tower_id.tower_floor_line_id.mapped('floors_orange'))
                    record.project_red = sum(record.tower_id.tower_flat_line_id.mapped('flats_red')) + sum(record.tower_id.tower_floor_line_id.mapped('floors_red'))
                    record.project_green = sum(record.tower_id.tower_flat_line_id.mapped('flats_green')) + sum(record.tower_id.tower_floor_line_id.mapped('floors_green'))

    def _compute_project_tower_progress_bar(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            try:
                for rec in self:
                    rec.project_tower_progress = 0
                    if rec.tower_id.tower_floor_line_id or rec.tower_id.tower_flat_line_id:
                        total_line = len(rec.tower_id.tower_floor_line_id.filtered(lambda obj: obj.floor_progress_percentage != 0.0)) + \
                                        len(rec.tower_id.tower_flat_line_id.filtered(lambda obj: obj.flats_progress_percentage != 0.0))
                        count_percent = sum(rec.tower_id.tower_floor_line_id.mapped('floor_progress_percentage')) + sum(
                            rec.tower_id.tower_flat_line_id.mapped('flats_progress_percentage'))
                        total_percent = total_line * 100
                        if total_percent:
                            rec.project_tower_progress = round((count_percent / total_percent) * 100)
            except Exception as e:
                _logger.info("Failed  _compute_project_tower_progress_bar-----,%s",str(e))
                pass
    
    # def generate_seq_floors(self):
    #     if self.project_info_tower_line_temp:
    #         for building in self.project_info_tower_line_temp:
    #             if building.tower_id:
    #                 building_name = building.name

    #                 for floor in building.tower_id.tower_floor_line_id:
    #                     floor_name = floor.name
    #                     activity_seq = '001'
    #                     for activity in floor.activity_ids:
    #                         #_logger.info("-------activity.name-------,%s",(activity.name))
    #                         if activity.name:
    #                             #activity_name = activity.name[:4].strip()
    #                             activity_name = activity.name

    #                             activity.index_no = activity_seq
    #                             new_number = int(activity_seq) + 1
    #                             activity_seq = '{:03d}'.format(new_number)
    #                             activity_type_seq = '001'
    #                             for activity_type in activity.activity_type_ids:
    #                                 no = 1 + 1
    #                                 temp = activity_type_seq
    #                                 activity_type.index_no = activity_type_seq
    #                                 new_number = int(activity_type_seq) + 1
    #                                 activity_type_seq = '{:03d}'.format(new_number)
    #                                 activity_type.seq_no = "VJD"+"/"+ str(self.name) +"/" + str(building_name) + "/" + str(floor_name) +"/" + str(activity_name) + "/" + str(temp)


    def generate_seq_flats_floors(self):
        if self.tower_id:
            project_name = False
            tower_name = self.tower_id.name
            if self.tower_id.project_id:
                project_name = self.tower_id.project_id.name
            for flat in self.tower_id.tower_flat_line_id:
                flat_name = flat.name
                activity_seq = '001'
                for activity in flat.activity_ids:
                    #_logger.info("-------activity.name-------,%s",(activity.name))
                    if activity.name:
                        #activity_name = activity.name[:4].strip()
                        activity_name = activity.name
                        activity.index_no = activity_seq
                        new_number = int(activity_seq) + 1
                        #activity_seq = '{:03d}'.format(new_number)
                        activity_type_seq = '001'
                        for activity_type in activity.activity_type_ids:
                            no = 1 + 1
                            temp = activity_type_seq
                            activity_type.index_no = activity_type_seq
                            new_number = int(activity_type_seq) + 1
                            activity_type_seq = '{:03d}'.format(new_number)
                            activity_type.seq_no = "VJD"+"/"+ str(project_name) +"/" + str(tower_name) + "/" + str(flat_name) +"/" + str(activity_name) + "/" + str(temp)
                            #print ("--activity_type.seq_no--",activity_type.seq_no)
                           
            for floor in self.tower_id.tower_floor_line_id:
                floor_name = floor.name
                activity_seq = '001'
                for activity in floor.activity_ids:
                    #_logger.info("-------activity.name-------,%s",(activity.name))
                    if activity.name:
                        #activity_name = activity.name[:4].strip()
                        activity_name = activity.name

                        activity.index_no = activity_seq
                        new_number = int(activity_seq) + 1
                        activity_seq = '{:03d}'.format(new_number)
                        activity_type_seq = '001'
                        for activity_type in activity.activity_type_ids:
                            no = 1 + 1
                            temp = activity_type_seq
                            activity_type.index_no = activity_type_seq
                            new_number = int(activity_type_seq) + 1
                            activity_type_seq = '{:03d}'.format(new_number)
                            activity_type.seq_no = "VJD"+"/"+ str(project_name) +"/" + str(tower_name) + "/" + str(floor_name) +"/" + str(activity_name) + "/" + str(temp)


# class ProjectInfoTowerTwo(models.Model):
#     _name = 'project.info.tower.two'


#     project_info_id_two = fields.Many2one('project.info','Two')
#     tower_id_two = fields.Many2one('project.tower',string="Tower")


class ProjectDetails(models.Model):
    _name = 'project.details'
    _description = "ProjectDetails"


    name = fields.Char('Name')
    image = fields.Binary("Image")
    # tower_id = fields.Many2one("project.tower", 'Tower')
    project_info_id = fields.Many2one('project.info', 'Project Id')
    tower_id = fields.Many2many('project.tower',string="Tower")

    # @api.onchange('tower_id')
    # def _onchange_tower_id(self):
    #     #_logger.info("---onchange project_details_line---")
    #     _logger.info("---onchange tower_id-----,%s",(self))
    #     #project_info_tower_line_temp = self.project_info_tower_line_temp  # Existing records in temp_line2

    #     # Clear existing temp_line2 records

    #     # Create new temp_line2 records based on temp_line1
    #     new_temp_line2_records = []
    #     tower_ids = []
    #     for tower_id in self:
    #         #_logger.info("---onchange ttower_id---,%s",(tower_id))
    #         tower_ids.append({'tower_id':tower_id.id,'name':tower_id.name,'project_id':self.id})
    #     _logger.info("---onchange tower_ids-----,%s",(tower_ids))

    #     if tower_ids:
    #         for tower_id in tower_ids:
    #             _logger.info("---tower_idtower_idtower_id---,%s",(tower_id))
    #             tw = tower_id['tower_id']
    #             _logger.info("---tower_idtower_idtower_id---,%s",(tw))
    #             tw = str(tw)
    #             ids = tw.split('_')
    #             _logger.info("--ids-,%s",(ids))
    #             _logger.info("--self.project_info_id.id-,%s",(self.project_info_id.id))



    #             temp = self.env['project.info.tower.line.temp'].search([('project_id','=',int(self.project_info_id.id)),('tower_id','=',int(ids[1]))])
    #             _logger.info("--temptemp--,%s",(temp))
                
        # if tower_ids:
        #     if project_info_tower_line_temp:
        #         project_info_tower_line_temp.unlink()
        #     _logger.info("--records creatimng----,%s",(self))
        #     _logger.info("--records creatimng----,%s",(self))
        #     _logger.info("--records creatimng----,%s",(self))
        #     _logger.info("--records creatimng----,%s",(self))
        #     _logger.info("--records creatimng----,%s",(self))
            #self.project_info_tower_line_temp.create(tower_ids)
            # vals = {
            #     'field1': line1.field1,  # Replace with actual field names
            #     'field2': line1.field2,
            #     'project_info_id': self.id,  # Link to project.info record
            # }
            # new_temp_line2_records.append((0, 0, vals))

        # Assign new records to temp_line2
        # self.temp_line2 = new_temp_line2_records



    # @api.onchange('tower_id')
    # def _onchange_tower_id_id(self):
    #     # Perform actions based on product_id change
    #     for line in self:
    #         print ("--line--",line)
    #         _logger.info("----------user_record---------,%s",line)



class ResUsers(models.Model):
    _inherit = 'res.users'


    lat = fields.Char('Latitude')
    longi = fields.Char('Longitude')

    def get_player_id(self,user_id):
        #_logger.info("----------groups self,user_id---------,%s,%s",self,user_id)

        user_record = self.browse(user_id)
        #_logger.info("----------user_record---------,%s",user_record)

        ids = ''
        if user_record:
            try:
                name = user_record.name
                #_logger.info("------user_record.player_line_ids-------,%s",user_record.player_line_ids)

                for player_id in user_record.player_line_ids:
                    #_logger.info("-----player_id------,%s",player_id)
                    ids = player_id.player_id
                    #_logger.info("-----player_id------,%s",ids)
                    break
            except Exception as e:
                _logger.info("-----eeeeee------,%s",str(e))

                pass
        return ids,user_record


    
