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



class ChecklistAllocationLine(models.Model):
    _name = 'checklist.allocation.line'
    _description = "ChecklistAllocationLine"


    checklist_allocation_floor_id = fields.Many2one('checklist.allocation','CK Floor')
    checklist_allocation_flat_id = fields.Many2one('checklist.allocation','CK Flat')
    chk_flat_id = fields.Many2one('checklist.allocation','CK Flat')
    chk_floor_id = fields.Many2one('checklist.allocation','CK Flat')
    project_activity_name_ids = fields.Many2many('project.activity.name')
    project_activity_name_flat_id = fields.Many2one('project.activity.name',string = 'Flat Activity Name')# for flat
    project_activity_name_floor_id = fields.Many2one('project.activity.name',string = 'Floor Activity Name')# for Floor
    flat_id = fields.Many2one('project.flats',string = 'Flat')
    flat_ids = fields.Many2many('project.flats',string = 'Flat')
    floor_ids = fields.Many2many('project.floors',string = 'Floor')
    floor_id = fields.Many2one('project.floors',string = 'Floor')# for Floor
    is_created = fields.Selection([('yes','Yes'),('no','No')],default="no", string='Is Created')
    sequence = fields.Integer(default=10,help="Gives the sequence order when displaying a list of records.")

    def create_floors_activity(self):
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']
        checklist_allocation_line_obj = self.env['checklist.allocation.line']

        if self.floor_ids:
            tower = self.chk_floor_id.tower_id
            for allocation_line in self.chk_floor_id.checklist_allocation_floor_ids:
                activity = allocation_line.project_activity_name_floor_id
                for floor_line in self.floor_ids:
                    floor = floor_line
                    act_created = project_activity_obj.search([('project_id','=',floor.project_id.id),('floor_id','=',floor.project_floor_id.id),('project_activity_name_id','=',activity.id),('tower_id','=',tower.id)])
                    if not act_created:
                        project_activity_data = {'project_activity_name_id':activity.id,'description':activity.description,'name':activity.name,'floor_id':floor.project_floor_id.id,'tower_id':floor.tower_id.id,'project_id':floor.project_id.id,'floor_id':floor.id}
                        activity_rec = project_activity_obj.create(project_activity_data)
                        allocation_line.is_created = 'yes'
                        for activity_type in activity.panl_ids:
                            project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':floor.project_id.id,'tower_id':floor.tower_id.id,'floor_id':floor.id}
                            activity_type_re = project_activity_type_obj.create(project_activity_type_data)
                            checklist_data = []
                            for chk in activity_type.patn_id.patnl_ids:
                                checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
                            project_checklist_line_obj.create(checklist_data)
                        rec = checklist_allocation_line_obj.search([('floor_id','=',floor.id),('chk_flat_id','=', self.id)])
                        rec.is_created = 'yes'
                        self.is_created = 'yes'
        return


    def create_flats_activity(self):
        project_activity_obj = self.env['project.activity']
        project_activity_type_obj = self.env['project.activity.type']
        project_checklist_line_obj = self.env['project.checklist.line']
        checklist_allocation_line_obj = self.env['checklist.allocation.line']

        if self.flat_ids:
            tower = self.chk_flat_id.tower_id
            for allocation_line in self.chk_flat_id.checklist_allocation_flat_ids:
                activity = allocation_line.project_activity_name_flat_id
                for flat_line in self.flat_ids:
                    flat = flat_line
                    act_created = project_activity_obj.search([('project_id','=',flat.project_id.id),('flat_id','=',flat.project_flat_id.id),('project_activity_name_id','=',activity.id),('tower_id','=',tower.id)])
                    if not act_created:
                        project_activity_data = {'project_activity_name_id':activity.id,'description':activity.description,'name':activity.name,'flat_id':flat.project_flat_id.id,'tower_id':flat.tower_id.id,'project_id':flat.project_id.id,'floor_id':flat.floor_id.id or ''}
                        activity_rec = project_activity_obj.create(project_activity_data)
                        allocation_line.is_created = 'yes'
                        for activity_type in activity.panl_ids:
                            project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':flat.project_id.id,'tower_id':flat.tower_id.id,'flat_id':flat.project_flat_id.id,'floor_id':flat.floor_id.id or ''}
                            activity_type_re = project_activity_type_obj.create(project_activity_type_data)
                            checklist_data = []
                            for chk in activity_type.patn_id.patnl_ids:
                                checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
                            project_checklist_line_obj.create(checklist_data)
                        rec = checklist_allocation_line_obj.search([('flat_id','=',flat.id),('chk_flat_id','=', self.id)])
                        rec.is_created = 'yes'
                        self.is_created = 'yes'
        return


class ChecklistAllocation(models.Model):
    _name = 'checklist.allocation'
    _rec_name = 'tower_id'
    _description = "ChecklistAllocation"


    tower_id = fields.Many2one('project.tower','Tower',required=1)
    #project_activity_name_ids = fields.Many2one('checklist.allocation.line','checklist_allocation_id')
    checklist_allocation_floor_ids = fields.One2many('checklist.allocation.line','checklist_allocation_floor_id')
    checklist_allocation_flat_ids = fields.One2many('checklist.allocation.line','checklist_allocation_flat_id')
    flat_ids = fields.One2many('checklist.allocation.line','chk_flat_id')
    floor_ids = fields.One2many('checklist.allocation.line','chk_floor_id')


    def action_load_floor_activity(self):
        self.checklist_allocation_floor_ids.unlink()
        activity_names = self.env['project.activity.name'].search([]).ids
        checklist_al = []
        for id in activity_names:
            checklist_al.append({'checklist_allocation_floor_id': self.id, 'project_activity_name_floor_id': id})
        if checklist_al:
            self.env['checklist.allocation.line'].create(checklist_al)
        return

    def action_sync_floors(self):
        checklist_allocation_line_obj = self.env['checklist.allocation.line']
        if self.tower_id:
            self.floor_ids.unlink()
            tower = self.tower_id
            floors = self.env['project.floors'].search([('tower_id','=',tower.id)]).ids
            if floors:
                group_size = 5
                groups = []
                for i in range(0, len(floors), group_size):
                    groups.append(floors[i:i + group_size])
                for data in groups:
                    checklist_allocation_line_obj.create({
                            'chk_floor_id': self.id,
                            'floor_ids': [(6, 0, data)]  # Replace record_id_1 and record_id_2 with actual record ids
                        })
        return

    def action_sync_flats(self):
        checklist_allocation_line_obj = self.env['checklist.allocation.line']
        if self.tower_id:
            self.flat_ids.unlink()
            tower = self.tower_id
            flats = self.env['project.flats'].search([('tower_id','=',tower.id)]).ids
            if flats:
                group_size = 5
                groups = []
                for i in range(0, len(flats), group_size):
                    groups.append(flats[i:i + group_size])
                for data in groups:
                    checklist_allocation_line_obj.create({
                            'chk_flat_id': self.id,
                            'flat_ids': [(6, 0, data)]  # Replace record_id_1 and record_id_2 with actual record ids
                        })
        return

    def action_load_flat_activity(self):
        self.checklist_allocation_flat_ids.unlink()
        activity_names = self.env['project.activity.name'].search([]).ids
        checklist_al = []
        for id in activity_names:
            checklist_al.append({'checklist_allocation_flat_id': self.id, 'project_activity_name_flat_id': id})

        if checklist_al:
            self.env['checklist.allocation.line'].create(checklist_al)

        return

    # def action_create_flat_activity(self):
    #     project_activity_obj = self.env['project.activity']
    #     project_activity_type_obj = self.env['project.activity.type']
    #     project_checklist_line_obj = self.env['project.checklist.line']
    #     checklist_allocation_line_obj = self.env['checklist.allocation.line']
    #     if self.tower_id:
    #         tower = self.tower_id
    #         flats = self.env['project.flats'].search([('tower_id','=',tower.id)]).ids
    #         flat_rec = []
    #         for id in flats:
    #             if not checklist_allocation_line_obj.search([('flat_id','=',id),('chk_flat_id','=',self.id)]):
    #                 flat_rec.append({'flat_id': id, 'chk_flat_id': self.id})
    #         if flat_rec:
    #             checklist_allocation_line_obj.create(flat_rec)
    #         for allocation_line in self.checklist_allocation_flat_ids:
    #             activity = allocation_line.project_activity_name_flat_id
    #             for flat_line in tower.tower_flat_line_id:
    #                 flat = flat_line
    #                 act_created = project_activity_obj.search([('project_id','=',flat.project_id.id),('flat_id','=',flat.project_flat_id.id),('project_activity_name_id','=',activity.id),('tower_id','=',tower.id)])
    #                 if not act_created:
    #                     project_activity_data = {'project_activity_name_id':activity.id,'description':activity.description,'name':activity.name,'flat_id':flat.project_flat_id.id,'tower_id':flat.tower_id.id,'project_id':flat.project_id.id,'floor_id':flat.floor_id.id or ''}
    #                     activity_rec = project_activity_obj.create(project_activity_data)
    #                     allocation_line.is_created = 'yes'
    #                     for activity_type in activity.panl_ids:
    #                         project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':flat.project_id.id,'tower_id':flat.tower_id.id,'flat_id':flat.project_flat_id.id,'floor_id':flat.floor_id.id or ''}
    #                         activity_type_re = project_activity_type_obj.create(project_activity_type_data)
    #                         checklist_data = []
    #                         for chk in activity_type.patn_id.patnl_ids:
    #                             checklist_data.append({'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id})
    #                         project_checklist_line_obj.create(checklist_data)
    #                     rec = checklist_allocation_line_obj.search([('flat_id','=',flat.id),('chk_flat_id','=', self.id)])
    #                     rec.is_created = 'yes'
    #     return

    # def action_create_floor_activity(self):
    #     project_activity_obj = self.env['project.activity']
    #     project_activity_type_obj = self.env['project.activity.type']
    #     project_checklist_line_obj = self.env['project.checklist.line']
    #     checklist_allocation_line_obj = self.env['checklist.allocation.line']
    #     if self.tower_id:
    #         tower = self.tower_id
    #         floors = self.env['project.floors'].search([('tower_id','=',tower.id)]).ids
    #         floor_rec = []
    #         for id in floors:
    #             if not checklist_allocation_line_obj.search([('floor_id','=',id),('chk_floor_id','=',self.id)]):
    #                 floor_rec.append({'floor_id': id, 'chk_floor_id': self.id})
    #         if floor_rec:
    #             checklist_allocation_line_obj.create(floor_rec)
    #         for allocation_line in self.checklist_allocation_floor_ids:
    #             activity = allocation_line.project_activity_name_floor_id
    #             for floor_line in tower.tower_floor_line_id:
    #                 floor = floor_line
    #                 act_created = project_activity_obj.search([('project_id','=',floor.project_id.id),('floor_id','=',floor.project_floor_id.id),('project_activity_name_id','=',activity.id),('tower_id','=',tower.id)])
    #                 if not act_created:
    #                     project_activity_data = {'project_activity_name_id':activity.id,'description':activity.description,'name':activity.name,'floor_id':floor.project_floor_id.id,'tower_id':floor.tower_id.id,'project_id':floor.project_id.id}
    #                     activity_rec = project_activity_obj.create(project_activity_data)
    #                     allocation_line.is_created = 'yes'
    #                     for activity_type in activity.panl_ids:
    #                         project_activity_type_data = {'activity_id':activity_rec.id,'project_actn_id':activity_type.patn_id.id,'name':activity_type.patn_id.name,'project_id':floor.project_id.id,'tower_id':floor.tower_id.id,'floor_id':floor.project_floor_id.id}
    #                         activity_type_re = project_activity_type_obj.create(project_activity_type_data)
    #                         for chk in activity_type.patn_id.patnl_ids:
    #                             checklist_data = {'activity_type_id':activity_type_re.id,'checklist_template_id':chk.checklist_id.id}
    #                             project_checklist_line_obj.create(checklist_data)
    #                     rec = checklist_allocation_line_obj.search([('floor_id','=',floor.id),('chk_floor_id','=', self.id)])
    #                     rec.is_created = 'yes'

class ProjectTower(models.Model):
    _name = 'project.tower'
    _inherit = ['mail.thread']  # Add mail.thread for chatter
    _description = "Project Tower"
    
    #_rec_name = 'name'
    #_order = 'id desc'
    name = fields.Char('Name',tracking=True)
    user_id = fields.Many2one('res.users','User Name')
    hierarchy_id = fields.Integer("Hierarchy Id")
    project_id = fields.Many2one('project.info','Project')
    tower_id = fields.Many2one('project.tower','Tower')
    project_details_line_id = fields.Many2one('project.details', 'Project Details Line Id')
    flat_id = fields.Many2one('project.flats', 'Flats',tracking=True)
    floor_id = fields.Many2one('project.floors', 'Floors',tracking=True)
    tower_floor_line_id = fields.One2many('project.floors','tower_id',string="Tower Floor",tracking=True)
    tower_flat_line_id = fields.One2many('project.flats','tower_id',string="Tower Flat",tracking=True)
    checklist_ids = fields.One2many('project.checklist.line','tower_id')
    activity_ids = fields.One2many('project.activity', 'project_tower_id')
    development_activity_ids = fields.One2many('project.activity', 'project_tower_id_dev')
    image = fields.Binary('Image')
    assigned_to_ids = fields.Many2many('res.users',tracking=True)
    project_details_line = fields.One2many('project.details', 'project_info_id')
    project_info_tower_line = fields.One2many('project.info.tower', 'project_info_tower_id')
    project_id = fields.Many2one("project.info")
    project_nc = fields.Integer('NC')
    project_red = fields.Integer('Red Flag')
    project_orange = fields.Integer('Orange Flag')
    project_yellow = fields.Integer('Yellow Flag')
    project_green = fields.Integer('Green Flag')
    tower_progress_percentage = fields.Float(string="Progress")
    tower_type = fields.Selection(
    [('development', 'Development'),('other', 'Other'), ('residential', 'Residential')],
    default='residential',
    string="Tower Type",
    readonly=False)

    # @api.depends('tower_flat_line_id.flats_nc', 'tower_flat_line_id.flats_orange', 'tower_flat_line_id.flats_orange',
    #              'tower_flat_line_id.flats_red', 'tower_flat_line_id.flats_green', 'tower_floor_line_id.floors_nc', 'tower_floor_line_id.floors_orange', 'tower_floor_line_id.floors_yellow', 'tower_floor_line_id.floors_red', 'tower_floor_line_id.floors_green')
    def _compute_total_count_from_status_tower(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            # Perform some action if enabled
            for record in self:
                if record.tower_flat_line_id or record.tower_floor_line_id:
                    record.write({'project_nc': sum(record.tower_flat_line_id.mapped('flats_nc')) + sum(record.tower_floor_line_id.mapped('floors_nc')),
                    'project_orange': sum(record.tower_flat_line_id.mapped('flats_orange')) + sum(record.tower_floor_line_id.mapped('floors_orange')),
                    'project_yellow': sum(record.tower_flat_line_id.mapped('flats_yellow')) + sum(record.tower_floor_line_id.mapped('floors_yellow')),
                    'project_red': sum(record.tower_flat_line_id.mapped('flats_red')) + sum(record.tower_floor_line_id.mapped('floors_red')),
                    'project_green': sum(record.tower_flat_line_id.mapped('flats_green')) + sum(record.tower_floor_line_id.mapped('floors_green'))
                    })

    def _compute_tower_progress_bar(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
        
            for rec in self:
                rec.tower_progress_percentage = 0
                if rec.tower_floor_line_id or rec.tower_flat_line_id:
                    total_line = len(rec.tower_floor_line_id.filtered(lambda obj: obj.floor_progress_percentage != 0.0)) + \
                                len(rec.tower_flat_line_id.filtered(lambda obj: obj.flats_progress_percentage != 0.0))
                    count_percent = sum(rec.tower_floor_line_id.mapped('floor_progress_percentage')) + sum(rec.tower_flat_line_id.mapped('flats_progress_percentage'))
                    total_percent = total_line * 100
                    if total_percent > 0:
                        rec.tower_progress_percentage = round((count_percent / total_percent) * 100, 2)
                        rec.project_id._compute_tower_progress_bar()

    def get_project_towers(self,project_info_id):
        #tower_data = self.search([('project_id','=',project_info_id)])
        tower_data = self.search_read([('project_id','=',project_info_id)], ['id', 'name'])
        return tower_data




class ProjectFlats(models.Model):
    _name = 'project.flats'
    _inherit = ['mail.thread']  # Add mail.thread for chatter

    _description = "Project Flats"

    #_order = 'id desc'

    name = fields.Char('Name')
    flat_id = fields.Integer(string='Flat Num')
    vj_floor_id = fields.Integer(string='VJ Floor ID')
    unit_type_id = fields.Integer(string='VJ Flat ID')
    tower_id = fields.Many2one('project.tower','Tower Name')
    project_id = fields.Many2one('project.info','Project')
    floor_id = fields.Many2one('project.floors','Floor Name')
    project_flat_id = fields.Many2one('project.flats','Flat Name')
    project_activity_name_id = fields.Many2one('project.activity.name','Activity Name')
    p_activity_id = fields.Many2one('project.activity', 'Activity Id')
    activity_ids = fields.One2many('project.activity', 'flat_id')
    flats_nc = fields.Integer('NC')
    flats_red = fields.Integer('Red Flag')
    flats_orange = fields.Integer('Orange Flag')
    flats_yellow = fields.Integer('Yellow Flag')
    flats_green = fields.Integer('Green Flag')
    flats_progress_percentage = fields.Float(string="Progress")
    activity_state = fields.Selection(selection=[('draft', 'Draft'), ('created', 'Created')],default='draft',string="Activity State",readonly=True,store=True,tracking=True)

    @api.onchange('tower_id')
    def onchange_tower_id(self):
        if self.tower_id:
            self.project_id = self.tower_id.project_id.id

    @api.model
    def create(self, values):
        main_model = super(ProjectFlats, self).create(values)
        main_model.project_flat_id = main_model.id
        ProjectActivity = main_model.project_activity_name_id
        tower_id = main_model.tower_id

        # if ProjectActivity and tower_id:
        #     activity_id = self.env['project.activity'].create({'flat_id':main_model.id,'name':ProjectActivity.name,'project_activity_name_id':ProjectActivity.id,'tower_id':tower_id.id})
        #     for line in ProjectActivity.panl_ids:
        #         print ("--line.patn_id.id--",line.patn_id.patnl_ids)
        #         pct = self.env['project.activity.type'].create({'activity_id':activity_id.id,'project_actn_id':line.patn_id.id,'name':line.patn_id.name})
        #         for line2 in line.patn_id.patnl_ids:
        #             print ("-line2---",line2)
        #             self.env['project.checklist.line'].create({'activity_type_id':pct.id,'checklist_template_id':line2.checklist_id.id})

        #     main_model.p_activity_id = activity_id.id
        return main_model

    # def write(self, vals):
    #     res = super(ProjectFlats, self).write(vals)
    #     pa_obj = self.env['project.activity']
    #     pat_obj = self.env['project.activity.type']
    #     pcl_obj = self.env['project.checklist.line']
    #     self.p_activity_id.tower_id = self.tower_id.id
    #     self.p_activity_id.project_id = self.project_id.id
    #     for activity_id in self.activity_ids:
    #         pat_rec = pa_obj.search([('project_activity_name_id','=',activity_id.project_activity_name_id.id),('project_id','=',self.project_id.id),('flat_id','=',self.id),('tower_id','=',self.tower_id.id)])
    #         if len(pat_rec) == 1 and not pat_rec.activity_type_ids:
    #             for line in activity_id.project_activity_name_id.panl_ids:
    #                 pct = self.env['project.activity.type'].create({'activity_id':activity_id.id,'project_actn_id':line.patn_id.id,'name':line.patn_id.name})
    #                 for checklist in pct.project_actn_id.patnl_ids:
    #                     self.env['project.checklist.line'].create({'activity_type_id':pct.id,'checklist_template_id':checklist.checklist_id.id})

    #     return res

    @api.onchange('project_flat_id')
    def onchange_project_flat_id(self):
        if self.project_flat_id:
            name = self.project_flat_id.name or ''
            if name:
                self.name = name
        #self.flat_id = self.flat_id or ''

    # @api.depends('activity_ids.act_nc', 'activity_ids.act_orange', 'activity_ids.act_orange',
    #              'activity_ids.act_red', 'activity_ids.act_green')
    def _compute_total_count_from_status_flats(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                if record.activity_ids:
                    record.write({'flats_nc': sum(record.activity_ids.mapped('act_nc')),
                    'flats_orange': sum(record.activity_ids.mapped('act_orange')),
                    'flats_yellow': sum(record.activity_ids.mapped('act_yellow')),
                    'flats_red': sum(record.activity_ids.mapped('act_red')),
                    'flats_green': sum(record.activity_ids.mapped('act_green'))
                    })

    def _compute_flats_progress_bar(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                rec.flats_progress_percentage = 0
                if rec.activity_ids:
                    total_line = len(rec.activity_ids.filtered(lambda obj: obj.progress_percentage != 0.0))
                    count_percent = sum(rec.activity_ids.mapped('progress_percentage'))
                    total_percent = total_line * 100
                    if total_percent > 0:
                        rec.flats_progress_percentage = round((count_percent / total_percent) * 100)
                        rec.tower_id._compute_tower_progress_bar()


class ProjectFloors(models.Model):
    _name = 'project.floors'
    _inherit = ['mail.thread']  # Add mail.thread for chatter
    _description = "Project Floors"

    #_order = 'id desc'
    name = fields.Char('Name')
    floor_id = fields.Integer(string='Floor Num')
    hirerchy_id = fields.Integer(string='Hirerchy Id')
    vj_floor_id = fields.Integer(string='VJ FLoor ID')
    tower_id = fields.Many2one('project.tower','Tower Name')
    project_floor_id = fields.Many2one('project.floors','Floor Name')
    project_activity_name_id = fields.Many2one('project.activity.name','Activity Name')
    project_id = fields.Many2one('project.info','Project')
    activity_ids = fields.One2many('project.activity', 'floor_id')
    #project_activity_ids = fields.One2many('project.activity', 'project_activities')
    p_activity_id = fields.Many2one('project.activity', 'Activity Id',readonly="1")
    floor_progress_percentage = fields.Float(string="Progress")
    floors_nc = fields.Integer('NC')
    floors_red = fields.Integer('Red Flag')
    floors_orange = fields.Integer('Orange Flag')
    floors_yellow = fields.Integer('Yellow Flag')
    floors_green = fields.Integer('Green Flag')
    activity_state = fields.Selection(selection=[('draft', 'Draft'), ('created', 'Created')],default='draft',string="Activity State",readonly=True,store=True,tracking=True)

    @api.onchange('project_floor_id')
    def onchange_project_floor_id(self):
        if self.project_floor_id:
            name = self.project_floor_id.name or ''
            if name:
                self.name = name

    @api.onchange('tower_id')
    def onchange_tower_id(self):
        if self.tower_id:
            self.project_id = self.tower_id.project_id.id

    # @api.depends('activity_ids.act_nc','activity_ids.act_orange', 'activity_ids.act_orange',
    #              'activity_ids.act_red', 'activity_ids.act_green')
    def _compute_total_count_from_status_floors(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                if record.activity_ids:
                    record.write({'floors_nc': sum(record.activity_ids.mapped('act_nc')),
                    'floors_orange': sum(record.activity_ids.mapped('act_orange')),
                    'floors_yellow': sum(record.activity_ids.mapped('act_yellow')),
                    'floors_red': sum(record.activity_ids.mapped('act_red')),
                    'floors_green': sum(record.activity_ids.mapped('act_green'))
                    })

    @api.model
    def create(self, values):
        main_model = super(ProjectFloors, self).create(values)
        main_model.project_floor_id = main_model.id
        tower_id = main_model.tower_id

        return main_model

    # def write(self, vals):
    #     res = super(ProjectFloors, self).write(vals)
    #     #print ("--vals--",vals)
    #     pa_obj = self.env['project.activity']
    #     pat_obj = self.env['project.activity.type']
    #     pcl_obj = self.env['project.checklist.line']
    #     self.p_activity_id.tower_id = self.tower_id.id
    #     self.p_activity_id.project_id = self.project_id.id
    #     for activity_id in self.activity_ids:
    #         pat_rec = pa_obj.search([('project_activity_name_id','=',activity_id.project_activity_name_id.id),('project_id','=',self.project_id.id),('floor_id','=',self.id),('tower_id','=',self.tower_id.id)])
    #         if len(pat_rec) == 1 and not pat_rec.activity_type_ids:
    #             for line in activity_id.project_activity_name_id.panl_ids:
    #                 pct = pat_obj.create({'activity_id':activity_id.id,'project_actn_id':line.patn_id.id,'name':line.patn_id.name})
    #                 for checklist in pct.project_actn_id.patnl_ids:
    #                     pcl_obj.create({'activity_type_id':pct.id,'checklist_template_id':checklist.checklist_id.id})


    #     return res

   
    def _compute_floor_progress_bar(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                rec.floor_progress_percentage = 0
                if rec.activity_ids:
                    total_line = len(rec.activity_ids.filtered(lambda obj: obj.progress_percentage != 0.0))
                    count_percent = sum(rec.activity_ids.mapped('progress_percentage'))
                    total_percent = total_line * 100
                    if total_percent > 0:
                        rec.floor_progress_percentage = round((count_percent / total_percent) * 100)
                        rec.tower_id._compute_tower_progress_bar()


class ProjectActivity(models.Model):
    _name = 'project.activity'
    _description = "Project Activity"

    #_order = 'id desc'

    name = fields.Char('Name')
    count = fields.Integer('Count',store=True,default=1)
    project_activity_id = fields.Many2one('project.activity',"Activity Name")
    project_activity_name_id = fields.Many2one('project.activity.name',"Activity Name")
    description = fields.Html('Description',sanitize=False)
    activity_type_ids = fields.One2many('project.activity.type','activity_id')
    floor_id = fields.Many2one('project.floors')
    flat_id = fields.Many2one('project.flats')
    project_tower_id = fields.Many2one('project.tower')
    project_tower_id_dev = fields.Many2one('project.tower')
    progress_percentage = fields.Float(string="Progress")
    project_id = fields.Many2one('project.info',string='Project',compute="_compute_project_id",store=True)
    tower_id = fields.Many2one('project.tower',string='Tower',compute="_compute_tower_id",store=True)
    index_no = fields.Char("Index No")
    act_nc = fields.Integer('NC')
    act_red = fields.Integer('Red Flag')
    act_orange = fields.Integer('Orange Flag')
    act_yellow = fields.Integer('Yellow Flag')
    act_green = fields.Integer('Green Flag')
    act_type =fields.Selection([('common','Common'),('development','Development')],default='',string="Type")
    status = fields.Selection([('draft','Draft'),('submit','Submit'),('checked','Checked'),('approve','Approved')],default='draft',string="Status")
    # state added to check all the activity type are completed or not
    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
    ], string="Status", default='draft', compute="_compute_status", store=True)

    @api.depends('activity_type_ids.status')
    def _compute_status(self):
        _logger.info("---_compute_status--")

        for record in self[0]:
            _logger.info("---_compute_status--")
            # Check if there are activity type records and if all are approved
            if record.activity_type_ids and all(at.status == 'approved' for at in record.activity_type_ids):
                record.status = 'completed'
            else:
                record.status = 'draft'
    
    @api.model
    def create(self, values):
        main_model = super(ProjectActivity, self).create(values)
        main_model.project_activity_id = main_model.id
        return main_model

    @api.onchange('project_activity_name_id')
    def onchange_project_activity_name_id(self):
        if self.project_activity_name_id:
            name = self.project_activity_name_id.name or ''
            if name:
                self.name = name

    @api.onchange('project_activity_id')
    def onchange_project_activity_id(self):
        if self.project_activity_id:
            name = self.project_activity_id.name or ''
            if name:
                self.name = name

    # @api.depends('activity_type_ids.act_type_nc', 'activity_type_ids.act_type_orange', 'activity_type_ids.act_type_orange', 'activity_type_ids.act_type_red', 'activity_type_ids.act_type_green')
    def _compute_total_count_from_status_act(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                if record.activity_type_ids:
                    record.write({'act_nc': sum(record.activity_type_ids.mapped('act_type_nc')),
                    'act_orange': sum(record.activity_type_ids.mapped('act_type_orange')),
                    'act_yellow': sum(record.activity_type_ids.mapped('act_type_yellow')),
                    'act_red': sum(record.activity_type_ids.mapped('act_type_red')),
                    'act_green': sum(record.activity_type_ids.mapped('act_type_green'))
                    })

    @api.depends('floor_id','flat_id')
    def _compute_tower_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                if rec.floor_id and rec.floor_id.tower_id:
                    rec.tower_id=rec.floor_id.tower_id.id
                elif rec.flat_id and rec.flat_id.tower_id:
                    rec.tower_id=rec.flat_id.tower_id.id

    @api.depends('floor_id','flat_id')
    def _compute_project_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                if rec.floor_id and rec.floor_id.tower_id and rec.floor_id.tower_id.project_id:
                    rec.project_id=rec.floor_id.tower_id.project_id.id
                elif rec.flat_id and rec.flat_id.tower_id and rec.flat_id.tower_id.project_id:
                    rec.project_id=rec.flat_id.tower_id.project_id.id


    def _compute_progress_bar(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                activity_type_ids = rec.activity_type_ids
                total_lines = len(activity_type_ids.filtered(lambda obj: obj.progress_percentage != 0.0))
                count = sum(1 for line in activity_type_ids if line.status not in ['draft', 'submit'])
                rec.progress_percentage = (count / total_lines) * 100 if total_lines > 0 else 0
                rec.floor_id._compute_floor_progress_bar()
                rec.flat_id._compute_flats_progress_bar()

class ProjectActivityType(models.Model):
    _name = 'project.activity.type.image'
    _description = "ProjectActivityType"


    activity_type_id = fields.Many2one('project.activity.type','Activity Type')
    overall_img = fields.Binary('Image')
    url = fields.Char("URL")
    img_type = fields.Selection([('pat','PAT'),('other','Other')],default='pat',string="Image Type")

  
class ProjectActivityType(models.Model):
    _name = 'project.activity.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name="display_name"
    _description = "Project ActivityType"

    def _get_display_name(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                    if rec.activity_id and rec.activity_id.floor_id and rec.activity_id.floor_id.tower_id and rec.activity_id.floor_id.tower_id.project_id:
                        rec.display_name=str(rec.activity_id.floor_id.tower_id.project_id.name) +"-"+str(rec.name)
                    elif rec.activity_id and rec.activity_id.flat_id and rec.activity_id.flat_id.tower_id and rec.activity_id.flat_id.tower_id.project_id:
                        rec.display_name=str(rec.activity_id.flat_id.tower_id.project_id.name) +"-"+ str(rec.name)
                    else:
                        rec.display_name==rec.name

    name = fields.Char('Name')
    seq_no = fields.Char('Sequence',readonly=1,store=True)
    activity_type_img_ids = fields.One2many('project.activity.type.image','activity_type_id')
    project_activity_type_id = fields.Many2one('project.activity.type','Activity Type')
    project_actn_id = fields.Many2one('project.activity.type.name','Activity Type Name')
    overall_remarks = fields.Char()
    display_name = fields.Char('Display Name',compute="_get_display_name")
    is_white_paper_ok = fields.Selection([('yes','Yes'),('no','No')],
                                         default="yes", string='Is white paper ok ?')
    comment = fields.Html('Comment/Remark')
    activity_id = fields.Many2one('project.activity')
    image_ids = fields.Many2many('ir.attachment', 'project_info_image_rel', 'project_info_id', 'image_id', string='Images')
    activity_image = fields.Binary("Image")
    checklist_ids = fields.One2many('project.checklist.line','activity_type_id')
    type_status=fields.Selection([('draft','Draft'),
                            ('submit','Submit'),
                            ('checked','Checked'),
                            ('approve','Approved'),('checker_reject','Checker Rejected'),
                            ('approver_reject','Approver Rejected')],default='draft',string="Type Status")
    status=fields.Selection([('draft','Draft'),
                            ('submit','Submit'),
                            ('checked','Checked'),
                            ('approve','Approved'),('checker_reject','Checker Rejected'),
                            ('approver_reject','Approver Rejected')],default='draft',string="Status")
    act_type_nc = fields.Integer('NC')
    act_type_red = fields.Integer('Red Flag')
    act_type_orange = fields.Integer('Orange Flag')
    act_type_yellow = fields.Integer('Yellow Flag')
    act_responsible_person = fields.Many2one('res.partner', 'Responsible Person')
    act_type_green = fields.Integer('Green Flag')
    #index_no = fields.Integer("Index No")
    index_no = fields.Char(string='Index No', help="Sequence for sorting")
    progress_percentage = fields.Float(string="Progress")
    project_id = fields.Many2one('project.info',string='Project',compute="_compute_project_id",store=True)
    flat_id = fields.Many2one(related="activity_id.flat_id",string='Flat')
    floor_id = fields.Many2one(related="activity_id.floor_id",string='Floor')
    tower_id = fields.Many2one('project.tower',string='Tower',compute="_compute_tower_id",store=True)
    checked_date = fields.Datetime("Checked Date")
    approved_date = fields.Datetime('Approved Date')
    user_maker = fields.Many2one('res.users','Maker')
    user_checker = fields.Many2one('res.users','Checker')
    user_approver = fields.Many2one('res.users','Approver')

    def write(self, vals):
        res = super(ProjectActivityType, self).write(vals)
        if 'state' in vals:
            for record in self.mapped('activity_id'):
                record._compute_status()  # Recalculate status in project.activity
        return res

    @api.model
    def get_c_m_a_data(self, project_id, tower, project_detailsValue):
        domain = []
        if tower:
            domain = [('tower_id', '=', int(tower))]
            # domain = [('tower_id', '=', int(tower)),('project_details_line.name', '=', project_detailsValue), ('project_details_line.tower_id', '=', int(tower))]
            project_list = self.tower_name_list(project_id, tower)
        elif project_id:
            domain = [('project_id', '=', int(project_id))]
            project_list = self.project_name_list(project_id, tower)

        projects = self.env['project.activity.type'].search(domain)

        # Initialize counts
        counts = {
            'Checker': 0,
            'Maker': 0,
            'Approver': 0
        }

        name = (projects[0].tower_id.name if tower else projects[0].project_id.name) if projects else ''

        # for activity in projects:
        #     if activity.status == 'checked' or activity.status == 'approve':
        #         counts['Checker'] += 1
        #     if activity.status == 'submit' or activity.status == 'checked' or activity.status == 'approve':
        #         counts['Maker'] += 1
        #     if activity.status == 'approve':
        #         counts['Approver'] += 1
        for activity in projects:
            if activity.status == 'draft':
                counts['Maker'] += 1
            elif activity.status == 'submit':
                counts['Checker'] += 1
            elif activity.status == 'checked':
                counts['Approver'] += 1

        graph_result = []
        for activity_type in ['Maker', 'Checker', 'Approver']:
            activity_counts = {name: counts[activity_type]}
            graph_result.append({'l_month': activity_type, 'leave': activity_counts})

        print('-----111graph_result------', graph_result)
        return graph_result, project_list


    # @api.model
    # def get_c_m_a_data(self, project_id, tower):
    #     domain = []
    #     project_info_model = self.env['project.info']  # Get the project.info model
    #     if tower:
    #         domain = [('tower_id', '=', int(tower))]
    #         project_list = project_info_model.tower_name_list(project_id, tower)
    #     elif project_id:
    #         domain = [('project_id', '=', int(project_id))]
    #         project_list = project_info_model.project_name_list(project_id, tower)
    #
    #     projects = self.env['project.activity.type'].search(domain)
    #     counts = {
    #         'Checker': {'Pending': 0, 'Completed': 0},
    #         'Maker': {'Pending': 0, 'Completed': 0},
    #         'Approver': {'Pending': 0, 'Completed': 0}
    #     }
    #
    #     name = (projects[0].tower_id.name if tower else projects[0].project_id.name) if projects else ''
    #
    #     for activity in projects:
    #         status = activity.status
    #         if status in ['checked', 'approve']:
    #             counts['Checker']['Pending'] += 1
    #         if status in ['submit', 'checked', 'approve']:
    #             counts['Maker']['Pending'] += 1
    #         if status == 'approve':
    #             counts['Approver']['Pending'] += 1
    #
    #         if status == 'done':  # Assuming 'done' indicates completion
    #             if status in ['checked', 'approve']:
    #                 counts['Checker']['Completed'] += 1
    #             if status in ['submit', 'checked', 'approve']:
    #                 counts['Maker']['Completed'] += 1
    #             if status == 'approve':
    #                 counts['Approver']['Completed'] += 1
    #
    #     graph_result = []
    #     for role in ['Maker', 'Checker', 'Approver']:
    #         for status in ['Pending', 'Completed']:
    #             count = counts[role][status]
    #             graph_result.append({'status': f'{role} {status}', 'name': {name: count}})
    #
    #     return graph_result, project_list

    # For Maker
    @api.model
    def action_submit(self):

        # Get the active IDs (the selected records)
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            _logger.warning("No records selected for submission.")
            return
        records = self.browse(active_ids).filtered(lambda r: r.status == 'draft')
        # Perform your operation on the selected records
        records.write({'status': 'submit'})

    # For Checker   
    def action_check(self):
        # Get the active IDs (the selected records)
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            _logger.warning("No records selected for submission.")
            return
        records = self.browse(active_ids).filtered(lambda r: r.status == 'submit')
        checker_id = False
        for record in records:
            if record.project_id:
                if record.project_id.user_checker:
                    checker_id = record.project_id.user_checker.id
                    break


        if checker_id:
        # Perform your operation on the selected records
            records.write({'status': 'checked','type_status':'checked','user_checker':checker_id,'checked_date':fields.Datetime.now()})
      
    # For Approver
    def action_approve(self):
        # Get the active IDs (the selected records)
        active_ids = self.env.context.get('active_ids', [])
        _logger.info("-action_approve---active_ids--------%s", len(active_ids))
        if not active_ids:
            _logger.warning("No records selected for submission.")
            return
        records = self.browse(active_ids).filtered(lambda r: r.status == 'checked')
        approver_id = False
        for record in records:
            if record.project_id:
                if record.project_id.user_approver:
                    approver_id = record.project_id.user_approver.id
                    break
        if approver_id:
            # Perform your operation on the selected records
            _logger.info("--action_approve---active_ids--------%s", len(records))
            
            records.write({'status': 'approve','type_status':'approve','user_approver':approver_id,'approved_date':fields.Datetime.now()})

    @api.model
    def create(self, values):
        main_model = super(ProjectActivityType, self).create(values)
        main_model.project_activity_type_id = main_model.id
        return main_model

    @api.onchange('project_actn_id')
    def onchange_project_actn_id(self):
        if self.project_actn_id:
            name = self.project_actn_id.name or ''
            if name:
                self.name = name

    @api.onchange('project_activity_type_id')
    def onchange_project_activity_type_id(self):
        if self.project_activity_type_id:
            name = self.project_activity_type_id.name or ''
            if name:
                self.name = name


    @api.onchange('name')
    def _onchange_name(self):
      
        activity_name = self.activity_id.name
        if activity_name:
            activity_name = activity_name[:4].strip()
            self.seq_no = "VJD/" + str(self.project_id.name) +"/"+ str(self.tower_id.name) +"/"+ str(activity_name)+"/" + str(self.flat_id.name) + "/"+str(self.index_no)

    @api.depends('activity_id.floor_id','activity_id.flat_id')
    def _compute_tower_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                if rec.activity_id.floor_id and rec.activity_id.floor_id.tower_id:
                    rec.tower_id=rec.activity_id.floor_id.tower_id.id
                elif rec.activity_id.flat_id and rec.activity_id.flat_id.tower_id:
                    rec.tower_id=rec.activity_id.flat_id.tower_id.id

    @api.depends('activity_id.floor_id','activity_id.flat_id')
    def _compute_project_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for rec in self:
                if rec.activity_id.floor_id and rec.activity_id.floor_id.tower_id and rec.activity_id.floor_id.tower_id.project_id:
                    rec.project_id=rec.activity_id.floor_id.tower_id.project_id.id
                elif rec.activity_id.flat_id and rec.activity_id.flat_id.tower_id and rec.activity_id.flat_id.tower_id.project_id:
                    rec.project_id=rec.activity_id.flat_id.tower_id.project_id.id


    def _compute_progress_bar(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            activity_types = self.search([('checklist_ids', '!=', False),('checklist_ids.is_pass','=','yes')])
            for rec in activity_types:
                checklist_ids = rec.checklist_ids
                total_lines = len(checklist_ids)
                count = len(checklist_ids.filtered(lambda line: line.is_pass == 'yes'))
                rec.progress_percentage = (count / total_lines) * 100 if total_lines> 0 and count >0 else 0
                rec.activity_id._compute_progress_bar()


    # def get_users_data(self,name,value,seq_no,rec):
    #     notification_obj = self.env['app.notification']
    #     notification_log_obj = self.env['app.notification.log']
    #     _logger.info("----------get_users_data-------,%s,%s,%s,%s,%s",self,name,value,seq_no,rec)
    #     if self.project_id:
    #         _logger.info("---------got project id---------,%s", self.project_id)
    #         if self.project_id.assigned_to_ids:
    #             _logger.info("-------self.project_id.assign_to_ids--------,%s",self.project_id.assigned_to_ids)
    #             for user in self.project_id.assigned_to_ids:
    #                 groups = user.groups_id
    #                 _logger.info("----------groups submit---------,%s",groups)
    #                 for group in groups:
    #                     _logger.info("------groupname----%s",group.name)
    #                     sent = 0
    #                     if str(group.name) == 'Checker' and value == 'maker':
    #                         #_logger.info("---------checker- submitted--Maker-----")
    #                         player_id ,user_r = self.env['res.users'].get_player_id(user.id)
    #                         message = "CheckList No " +str(seq_no) + " Submitted by " + str(name)
    #                         #_logger.info("-----1----message-player_id--------,%s,%s",message,player_id)
    #                         #failed_message = {'player_id':player_id,'message':message,'user':user.name,'seq_no':seq_no,'value':value}
    #                         if player_id and message and user:
    #                             try:
    #                                 title = str(name) + " Submitted the Checklist"
    #                                 notification_obj.send_push_notification(title,[player_id],message,[user.id],rec,seq_no,'')
    #                                 sent = 1
    #                             except Exception as e:
    #                                 #_logger.info("-------1---exception---------,%s",str(e))
    #                                 #title = str(e)
    #                                 pass
    #                         #if not sent:
    #                             #notification_log_obj.sudo().create({'status':'failed','title':title,'res_user_id':user.id,'player_id':player_id,'table_id':rec.id})
    #                     sent = 0
    #                     if str(group.name) == 'Approver' and value == 'checker':
    #                         _logger.info("---------Approver---Checker--submitted by checker---")
    #                         player_id ,user_r = self.env['res.users'].get_player_id(user.id)
    #                         message = "CheckList No " +str(seq_no) + " Submitted by " + str(name)
    #                         _logger.info("----2-----message-player_id--------,%s,%s",message,player_id)
    #                         if player_id and message and user:
    #                             try:
    #                                 title = str(name) + " Submitted the Checklist"
    #                                 notification_obj.send_push_notification(title,[player_id],message,[user.id],rec,seq_no)
    #                                 sent = 1
    #                             except Exception as e:
    #                                 _logger.info("-------2---exception---------,%s",str(e))
    #                                 pass
    #                     sent = 0
    #                     if str(group.name) == 'Custom Admin' and value == 'approver':
    #                         _logger.info("---------Custom Admin--submitted by -approver-----")
    #                         player_id ,user_r = self.env['res.users'].get_player_id(user.id)
    #                         message = "CheckList No " +str(seq_no) + " Submitted by " + str(name)
    #                         _logger.info("----3-----message-player_id--------,%s,%s",message,player_id)
    #                         if player_id and message and user:
    #                             try:
    #                                 title = str(name) + " Submitted the Checklist"
    #                                 notification_obj.send_push_notification(title,[player_id],message,[user.id],rec,seq_no)
    #                                 sent = 1
    #                             except Exception as e:
    #                                 _logger.info("------3----exception---------,%s",str(e))
    #                                 pass
    # def get_users_data_reject(self,name,value,seq_no,rec):
    #     notification_obj = self.env['app.notification']
    #     _logger.info("----------get_users_data-------,%s,%s,%s,%s,%s",self,name,value,seq_no,rec)
    #     if self.project_id:
    #         _logger.info("---------got project id---------,%s", self.project_id)
    #         if self.project_id.assigned_to_ids:
    #             _logger.info("-------self.project_id.assign_to_ids--------,%s",self.project_id.assigned_to_ids)
    #             for user in self.project_id.assigned_to_ids:
    #                 groups = user.groups_id
    #                 _logger.info("----------groups submit---------,%s",groups)
    #                 for group in groups:
    #                     _logger.info("------groupname----%s",group.name)

    #                     if str(group.name) == 'Checker' and value == 'maker':
    #                         _logger.info("---------checker- submitted--Maker-----")
    #                         player_id ,user_r = self.env['res.users'].get_player_id(user.id)
    #                         message = "CheckList No " +str(seq_no) + " Rejected by " + str(name)
    #                         _logger.info("-----1----message-player_id--------,%s,%s",message,player_id)
    #                         if player_id and message and user:
    #                             try:
    #                                 title = str(name) + " Rejected the Checklist"
    #                                 notification_obj.send_push_notification(title,[player_id],message,[user.id],rec,seq_no)
    #                             except Exception as e:
    #                                 _logger.info("-------1---exception---------,%s",str(e))
    #                                 pass
    #                     if str(group.name) == 'Approver' and value == 'checker':
    #                         _logger.info("---------Approver---Checker--submitted by checker---")
    #                         player_id ,user_r = self.env['res.users'].get_player_id(user.id)
    #                         message = "CheckList No " +str(seq_no) + " Rejected by " + str(name)
    #                         _logger.info("----2-----message-player_id--------,%s,%s",message,player_id)
    #                         if player_id and message and user:
    #                             try:
    #                                 title = str(name) + " Rejected the Checklist"
    #                                 notification_obj.send_push_notification(title,[player_id],message,[user.id],rec,seq_no)
    #                             except Exception as e:
    #                                 _logger.info("-------2---exception---------,%s",str(e))
    #                                 pass
    #                     if str(group.name) == 'Custom Admin' and value == 'approver':
    #                         _logger.info("---------Custom Admin--submitted by -approver-----")
    #                         player_id ,user_r = self.env['res.users'].get_player_id(user.id)
    #                         message = "CheckList No " +str(seq_no) + " Rejected by " + str(name)
    #                         _logger.info("----3-----message-player_id--------,%s,%s",message,player_id)
    #                         if player_id and message and user:
    #                             try:
    #                                 title = str(name) + " Rejected the Checklist"
    #                                 notification_obj.send_push_notification(title,[player_id],message,[user.id],rec,seq_no)
    #                             except Exception as e:
    #                                 _logger.info("------3----exception---------,%s",str(e))
    #                                 pass

    # Update checklist maker sending to checker
    def button_submit(self,seq_no=None,user_id=None):
        _logger.info("----------button submit---------,%s,%s,%s", self,seq_no,user_id)
        
        self.status='submit'
        self.type_status = 'submit'

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
                                    log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'wi',self)
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

        return True

    # update_checklist_checker sending to approver # Checker to approver
    def button_checking_done(self,seq_no=None,user_id=None):
        _logger.info("----------button_checking_done-------,%s,%s", self,user_id)
        self.status='checked'
        self.type_status='checked'

        rec = self
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
            #if self.project_id.assigned_to_ids:
            if self.tower_id.assigned_to_ids:
                failed_log.update({'assigned_ids':self.tower_id.assigned_to_ids})
                #_logger.info("-- button_checking_done -----self.project_id.assign_to_ids--------,%s",self.project_id.assigned_to_ids)
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
                                    log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'wi',self)
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
        return


    # update_checklist_approver Approver to custom admin
    def button_approve(self,seq_no=None,user_id=None):

        app_log_obj = self.env['app.notification.log']
        notification_obj = self.env['app.notification']
        rec = self
        log_id = False
        group_name_not_found = 1
        sent = 0
        failed_log = {}

        self.status='approve'
        self.type_status = 'approve'
        _logger.info("----------button_approve-------,%s,%s,%s", self,seq_no,user_id)
        failed_log.update({'seq_no':seq_no,'user_id':user_id,'method':'button_approve'})

        try:
            if self:
                rec = app_log_obj.search([('activity_type_id','=',self.id)])
                if rec:
                    rec.write({'checklist_status':'approve','checklist_status_two':'approve'})
        except Exception as e:
            _logger.info("---button_approve notification-----,%s",str(e))
            pass

        # Commented this code because there is no custom admin user right now
        # if user_id:
        #     player_id = ''
        #     message = ''
        #     #user , player_id  = self.env['res.users'].get_player_id(user_id)
        #     user_record = self.env['res.users'].browse(user_id)
        #     #user_groups = user_record.groups_id
        #     #self.get_users_data(user_record.name,'maker',seq_no,rec)
        #     if self.tower_id.assigned_to_ids:
        #         failed_log.update({'assigned_ids':self.tower_id.assigned_to_ids})

        #         #_logger.info("-- button_approve -----self.project_id.assign_to_ids--------,%s",self.project_id.assigned_to_ids)
        #         for user in self.tower_id.assigned_to_ids:
        #             groups = user.groups_id
        #             #_logger.info("---button_approve-------groups ---------,%s",groups)
        #             for group in groups:
        #                 #_logger.info("------groupname----%s",group.name)
        #                 if str(group.name) == 'Custom Admin':
        #                     failed_log.update({'group_name':'Custom Admin'})
        #                     group_name_not_found = 0

        #                     #_logger.info("----button_approve----checker to approver-----")
        #                     player_id ,user_r = self.env['res.users'].get_player_id(user.id)
        #                     message = "CheckList No " +str(seq_no) + " Submitted by " + str(user_record.name)
        #                     #_logger.info("--button_approve---1----message-player_id--------,%s,%s",message,player_id)
        #                     e = ''
        #                     if player_id and message and user:
        #                         try:
        #                             title = str(user_record.name) + " Submitted the Checklist"
        #                             log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'wi',self)
        #                             sent = 1
        #                         except Exception as e:
        #                             #_logger.info("----button_approve---1---exception---------,%s",str(e))
        #                             pass
        #                     else:
        #                         failed_log.update({'player_id':player_id,'message':message,'user':user,'error':str(e)})
        #             if group_name_not_found:
        #                 failed_log.update({'group_name':'custom admin group name not found'})
        #     else:
        #         failed_log.update({'ids_not_found':'Assigned Ids Not Found'})

        # if not sent and not log_id:
        #     self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})
     
        self.approved_date = fields.Datetime.now()
        return

    # @api.depends('checklist_ids.project_line_nc', 'checklist_ids.project_line_red', 'checklist_ids.project_line_orange', 'checklist_ids.project_line_yellow')
    def _compute_total_count_from_status_act_type(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            for record in self:
                if record.checklist_ids:
                    record.write({'act_type_nc': sum(record.checklist_ids.mapped('project_line_nc')),
                    'act_type_orange': sum(record.checklist_ids.mapped('project_line_orange')),
                    'act_type_yellow': sum(record.checklist_ids.mapped('project_line_yellow')),
                    'act_type_red': sum(record.checklist_ids.mapped('project_line_red'))
                    })

        # commented to approve n
        #self.status='approve'

    def check_count_for_green(self):
        try:
            for record in self.search([('checklist_ids', '!=', False)]):
                # print ("---record----",record)
                # print ("---record----",record.checklist_ids)
                check_list = len(record.checklist_ids)
                yes_check_list = len(record.checklist_ids.filtered(lambda x:  x.is_pass and x.is_pass != 'yes'))
                record.act_type_green = record.act_type_green + 1 if check_list == yes_check_list else 0
        except Exception as e:
            _logger.info("--FAILED--check_count_for_green--------,%s",str(e))
            pass

    def button_set_to_draft(self,user_id=False):
        _logger.info("----------button_set_to_draft-------,%s,%s", self,user_id)
        self.status='draft'

    def button_set_to_maker(self,seq_no,user_id=False):
        _logger.info("---button_set_to_maker------self,seq_no,user_id---------,%s,%s,%s",self,seq_no,user_id)

        rec = self
        self.status='draft'
        self.type_status='checker_reject'
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

            _logger.info("---button_set_to_maker----self.user_maker--------,%s",self.user_maker)

            if not self.user_maker:

                if self.tower_id.assigned_to_ids:
                    failed_log.update({'assigned_ids':self.tower_id.assigned_to_ids})
                    for user in self.tower_id.assigned_to_ids:
                        groups = user.groups_id
                        for group in groups:
                            if str(group.name) == 'Maker':
                                failed_log.update({'group_name':'maker'})
                                group_name_not_found = 0
                                player_id ,user_r = self.env['res.users'].get_player_id(user.id)
                                message = "CheckList No " +str(seq_no) + " Rejected by " + str(user_record.name)
                                e = ''
                                if player_id and message and user:
                                    try:
                                        title = str(user_record.name) + " Rejected the Checklist"
                                        log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'wi',self)
                                        sent = 1
                                    except Exception as e:
                                        _logger.info("--wi1--button_set_to_maker---1---exception---------,%s",str(e))
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
                if player_id and message and user_record:
                    try:
                        title = str(user_record.name) + " Rejected the Checklist"
                        log_id = notification_obj.send_push_notification(title,[player_id],message,[self.user_maker.id],seq_no,'wi',self)
                        sent = 1
                    except Exception as e:
                        _logger.info("--wi2--button_set_to_maker---1---exception---------,%s",str(e))
                        pass
                else:
                    failed_log.update({'player_id':player_id,'message':message,'user':user})

        if not sent and not log_id:
            self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})
        return

    def button_set_to_checker(self,seq_no,user_id):
        _logger.info("---button_set_to_checker------self,seq_no,user_id---------,%s,%s,%s",self,seq_no,user_id)

        rec = self
        self.status='submit'
        self.type_status='approver_reject'
        
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
            user_groups = user_record.groups_id
            #self.get_users_data(user_record.name,'maker',seq_no,rec)

            if not self.user_checker:
                if self.project_id.assigned_to_ids:
                    failed_log.update({'assigned_ids':self.project_id.assigned_to_ids})

                    #_logger.info("-- button_set_to_checker -----self.project_id.assign_to_ids--------,%s",self.project_id.assigned_to_ids)
                    for user in self.project_id.assigned_to_ids:
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
                                        log_id = notification_obj.send_push_notification(title,[player_id],message,[user.id],seq_no,'wi',self)
                                        sent = 1
                                    except Exception as e:
                                        #_logger.info("----button_set_to_checker---1---exception---------,%s",str(e))
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
                        log_id = notification_obj.send_push_notification(title,[player_id],message,[self.user_checker.id],seq_no,'wi',self)
                        sent = 1
                    except Exception as e:
                        _logger.info("--wi3--button_set_to_maker---1---exception---------,%s",str(e))
                        pass
                else:
                    failed_log.update({'player_id':player_id,'message':message,'user':user})
        if not sent and not log_id:
            self.env['app.notification.log'].create({'title':failed_log,'status':'failed'})
        return

    def get_project_activity_details(self,activity_type_id):
        _logger.info("----------get_project_activity_details-------,%s",activity_type_id)

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')

        activity = self.browse(activity_type_id)
        #_logger.info("----------activityactivity-------,%s",activity)
        image_urls = []
        activity_status = activity.status
        if activity.status == 'approver_reject':
            activity_status='submit'
        if activity.status == 'checker_reject':
            activity_status='draft'

        reject = ''
        try:
            if activity.type_status:
                if activity.type_status == 'checker_reject' or activity.type_status == 'approver_reject':
                    reject = activity.type_status
        except Exception as e:
            _logger.info("------get_project_activity_details--reject-----,%s",str(e))
            pass

        ###
        try:

            line_data=[]
            #logs = self.env['project.checklist.line.log'].search([('activity_type_id','=',activity.id)])
            for checklist_line in activity.checklist_ids:
                history = []
                log_lines = self.env['project.checklist.line.log'].search([('line_id','=',checklist_line.id)])
                
                for line in log_lines:
                    image_link = []
                    for url_data in line.checklist_line_log_line:
                        image_link.append(url_data.url)
                    history.append({
                        'id':line.id,
                        'name':line.checklist_template_id.name,
                        'reason':line.reason,
                        'is_pass':line.is_pass,
                        'name':line.checklist_template_id.name,
                        'submittedBy':{'id':line.user_id.id,'name':line.user_id.name,'role':line.role},
                        'update_time':str(line.datetime),
                        'image_url':image_link,
                        'submitted':'false',
                        })
                
                image_link=[]
                for image_line in checklist_line.image_ids:
                    checklist_image_url = base_url+"/web/image?model=project.checklist.line.images&field=image&id="+str(image_line.id)
                    image_link.append(checklist_image_url)

                line_data.append({
                    'name':checklist_line.checklist_template_id.name,
                    'reason':checklist_line.reason,
                    'is_pass':checklist_line.is_pass,
                    'name':checklist_line.checklist_template_id.name,
                    'image_url':image_link,
                    'line_id':checklist_line.id,
                    'history':history
                    # 'submittedBy':{'id':user_id,'name':user_record.name,'role':role},
                    # 'update_time':datetime.datetime.now(),
                    })
        ###
        except Exception as e:
            _logger.info("-get_project_activity_details--history-----,%s",str(e))
            pass

        response = {
            "activity_name":activity.activity_id.name,
            "name": activity.name,
            "activity_type_id": activity.id,
            "activity_status": activity_status,
            "activity_type_progress": activity.progress_percentage,
            "project_id": activity.project_id.id,
            "project_name": activity.project_id.name,
            "flat": activity.flat_id.id,
            "flat_name": activity.flat_id.name,
            "tower_id": activity.tower_id.id,
            "tower_name": activity.tower_id.name,
            "floor_id": activity.floor_id.id,
            "floor_name": activity.floor_id.name,
            "overall_remarks":activity.overall_remarks or '',
            "overall_images":image_urls,
            "wi_status":reject,
            "line_data":line_data,
        }
        try:
            if activity.activity_type_img_ids:
                for img in activity.activity_type_img_ids:
                    if img.img_type == 'pat':
                        checklist_image_url= base_url +"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
                        image_urls.append(checklist_image_url)
           
            response['overall_images'] = image_urls

        except Exception as e:
            _logger.info("-get_project_activity_details--exception- overall_images-----,%s",str(e))
            pass
    
        # try:
        #     image_urls = []
        #     if activity.activity_type_img_ids:
        #         for img in activity.activity_type_img_ids:
        #             if img.img_type == 'pat':
        #                 checklist_image_url=url+"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
        #                 image_urls.append(checklist_image_url)
        #     response['overall_images'] = image_urls
        # except Exception as e:
        #     _logger.info("-get_project_activity_details--exception- overall_images-----,%s",str(e))
        #     pass


        ## Imp Code ##3
        
        # line_data = []
        # if activity.checklist_ids:
        #     for checklist in activity.checklist_ids:
        #         iamgedata = []
        #         data = {'line_id':checklist.id,'name':checklist.checklist_template_id.name,'reason':checklist.reason,'is_pass':checklist.is_pass}
        #         if checklist.image_ids:
        #             for image in checklist.image_ids:
        #                 _logger.info("----imp------image-----,%s",(image))
        #                 image_url=url+"/web/image?model=project.checklist.line.images&field=image&id="+str(image.id)
        #                 iamgedata.append(image_url)
        #         data['image_url'] = iamgedata
        #         line_data.append(data)
        # response['line_data'] = line_data
        # end  #

        #_logger.info("----------response-------,%s",(response))
        return response


class ProjectChecklistLine(models.Model):
    _name = 'project.checklist.line'
    _description = "Project Checklist Line"
    _rec_name = 'checklist_template_id'

    checklist_template_id = fields.Many2one('project.checklist.template')
    is_pass = fields.Selection([('yes', 'Yes'),
                                      ('no', 'No'),
                                      ('nop', 'Not Applicable'),
                                      ],string="status")
    submitted = fields.Selection([('true', 'True'),
                                      ('false', 'False'),
                                      ],default='true',string="Submitted")
    activity_type_id = fields.Many2one('project.activity.type')
    tower_id = fields.Many2one('project.tower','Tower ')
    reason = fields.Text("Reason")
    seq_no = fields.Char("Seq No",store=True)
    overall_remarks = fields.Char()
    image_ids = fields.One2many("project.checklist.line.images",'checklist_line_id',string="Images")
    project_line_nc = fields.Integer('NC')
    project_line_red = fields.Integer('Red Flag')
    project_line_orange = fields.Integer('Orange Flag')
    project_line_yellow = fields.Integer('Yellow Flag')
    project_line_cre_date = fields.Datetime('Checklist Create Date', default=lambda self: fields.Datetime.now() - timedelta(hours=5, minutes=30))
    image = fields.Binary()
    first_time_check = fields.Boolean('First time check',default=True)

    @api.onchange('image_ids', 'reason')
    def _onchange_image(self):
        value = self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False)
        if value:
            if self.image_ids:
                # Get the first image record directly
                first_image = self.image_ids[0]
                # Assign the binary data directly to self.image
                if first_image.image:
                    self.image = first_image.image
                else:
                    self.image = False  # Clear the image if there's no binary data
            else:
                self.image = False  # Clear the image if no images are available

    def is_days_difference_for_status_count(self):
        """Update project line status counters based on the days difference."""
        # Get today's date
        today_date = datetime.now()
        records = self.search([('is_pass', '=', 'no'), ('project_line_cre_date', '!=', False)])
        for rec in records:
            is_changed = False
            if rec.activity_type_id and rec.activity_type_id.status in ['checked'] :
                target_date = rec.project_line_cre_date
                # Calculate the difference in days
                calculated_days_difference = (today_date - target_date).days
                print('==========calculated_days_difference=======',rec.checklist_template_id.name,rec, calculated_days_difference)
                if calculated_days_difference in [2, 4, 7] or calculated_days_difference == 14:
                    if calculated_days_difference == 2:
                        rec.project_line_nc = 1
                    elif calculated_days_difference == 4:
                        rec.project_line_yellow = 1
                    elif calculated_days_difference == 7:
                        rec.project_line_orange = 1
                    elif calculated_days_difference == 14:
                        rec.project_line_red = 1
                    is_changed = True
                if is_changed:
                    activity_type_ids = self.env['project.activity.type'].search([('checklist_ids','in',rec.id),('status','in',['checked'])])
                    activity_type_ids._compute_total_count_from_status_act_type()
                    activity_ids = self.env['project.activity'].search([('activity_type_ids','in',activity_type_ids.ids)])
                    rec.activity_type_id.activity_id._compute_total_count_from_status_act()
                    floor_ids = self.env['project.floors'].search([('activity_ids','in',activity_ids.ids)])
                    floor_ids._compute_total_count_from_status_floors()
                    flat_ids = self.env['project.flats'].search([('activity_ids','in',activity_ids.ids)])
                    flat_ids._compute_total_count_from_status_flats()
                    tower_ids = self.env['project.tower'].search(['|',('tower_floor_line_id','in',floor_ids.ids),('tower_flat_line_id','in',flat_ids.ids)])
                    tower_ids._compute_total_count_from_status_tower()

                    activity_id = rec.activity_type_id.activity_id
                    # create manually flag
                    self.env['manually.set.flag'].create({'project_info_id': activity_id.project_id.id,
                                                        'project_tower_id': activity_id.tower_id.id,
                                                        'project_floor_id': activity_id.floor_id.id,
                                                        'project_flats_id': activity_id.flat_id.id,
                                                        'project_activity_id': activity_id.id,
                                                        'project_act_type_id': rec.activity_type_id.id,
                                                        'project_check_line_id': rec.id,
                                                        'project_responsible': self.env.user.partner_id.id,
                                                        'cre_nc': rec.project_line_nc,
                                                        'cre_yellow': rec.project_line_yellow,
                                                        'cre_orange': rec.project_line_orange,
                                                        'cre_red': rec.project_line_red,
                                                        'cre_Green': 0.,
                                                        'is_created': True,
                                                        'status': 'open',
                                                    })


    @api.onchange('is_pass')
    def onchange_status_for_mail(self):
        if self.is_pass and self.is_pass == 'yes':
            mail_template = self.env.ref('custom_project_management.email_status_set_to_yes_mail')
            mail_mail = self.env['mail.mail'].create({
                'subject': 'Activity: Email for activity status yes',
                'body_html': mail_template.body_html,
                'email_from': self.env.user.email or self.env.ref('base.user_root').email_formatted,
                'email_to': self.activity_type_id.act_responsible_person.email,
            })
            mail_mail.send()
        else:
            mail_template = self.env.ref('custom_project_management.email_status_set_to_no_mail')
            mail_mail = self.env['mail.mail'].create({
                'subject': 'Activity: Email for activity status no',
                'body_html': mail_template.body_html,
                'email_from': self.env.user.email or self.env.ref('base.user_root').email_formatted,
                'email_to': self.activity_type_id.act_responsible_person.email,
            })
            mail_mail.send()
        if self.first_time_check:
            if self.is_pass == 'yes':
                pass
            else:
                self.first_time_check = False

class ProjectChecklistLineImages(models.Model):
    _name = 'project.checklist.line.images'
    _order = 'id desc'
    _description = "Project Checklist Line Images"

    checklist_line_id = fields.Many2one('project.checklist.line')
    project_checklist_line_log_id = fields.Many2one('project.checklist.line.log')
    image = fields.Binary('File')
    filename = fields.Char("filename")

class ProjectChecklistTemplate(models.Model):
    _name = 'project.checklist.template'
    _order = 'id desc'
    _description = "ProjectChecklistTemplate"

    name = fields.Char('Name')
    tower_id = fields.Many2one('project.tower', string="Associated Tower")
    
class ProjectNc(models.Model):
    _name = 'project.nc'
    _order = 'id desc'
    _description = "ProjectNc"

    name = fields.Char('Name')

# class ProjectFlatsLine(models.Model):
#     _name = 'project.flats.line'

#     flat_tower_id = fields.Many2one('project.tower')
#     flat_line_id = fields.Many2one('project.flats')

# class ProjectFloorsLine(models.Model):
#     _name = 'project.floors.line'

#     floor_tower_id = fields.Many2one('project.tower')
#     floor_line_id =  fields.Many2one('project.floor')
