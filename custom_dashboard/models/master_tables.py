# -*- coding: utf-8 -*-
# from distutils.command.check import check
# from setuptools import setup
# from setuptools.command.check import check

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
_logger = logging.getLogger(__name__)


class ProjectActivityName(models.Model):
    _name = 'project.activity.name'
    _description = "ProjectActivityName"
    

    name = fields.Char("Name")
    realname = fields.Char("Real Name")
    description = fields.Html('Description')
    panl_ids = fields.One2many('project.activity.name.line','pan_id')
    status = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string="Status", default='draft')
    project_ids = fields.Many2many('project.info',string = 'Project(s)')
    type = fields.Selection([('floor', 'Floor'), ('flat', 'Flat')], string="Type 1")
    type_2 = fields.Selection([('common_area', 'Common Area'), ('development', 'Development')], string="Type 2")


    def load_projects(self):
        # rec = self.env['project.activity'].search([],limit=100).unlink()
        # return
        self.project_ids = [(6, 0, [])]
        pr_ids = self.env['project.info'].search([]).ids
        self.project_ids = [(6, 0, pr_ids)]
        return
    
    # def del_activity(self):
    #     rec = self.env['project.activity.type'].search([],limit=100).unlink()
    #     return

        # project_act_obj = self.env['project.activity']
        # if self.project_ids:
        #     for project_id in self.project_ids:
        #         act_records = project_act_obj.search([('project_activity_name_id','=',self.id),('project_id','=',project_id.id)])
        #         _logger.info("-----1act_records-------,%s",act_records)
        #         act_records.unlink()
                

    def update_name(self):
        # crd = self.id
        # records = self.env['project.activity'].search([('project_activity_name_id','=',crd)])
        # _logger.info("-----1----message-player_id--------,%s",records)
        # if self.realname:
        #     self.name = self.realname
        #     records.name = self.realname
        #     self.status = 'done'
        return True


class ProjectActivityNameLine(models.Model):
    _name = 'project.activity.name.line'
    _description = "ProjectActivityNameLine"

  
    name = fields.Char("Name")
    pan_id = fields.Many2one('project.activity.name','Activity Name')
    patn_id = fields.Many2one('project.activity.type.name','Activity Type Name')

class ProjectActivityTypeName(models.Model):
    _name = 'project.activity.type.name'
    _description = "ProjectActivityTypeName"


    name = fields.Char("Name")
    patnl_ids = fields.One2many('project.activity.type.name.line','patn_id')
    realname = fields.Char("Real Name")
    status = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string="Status", default='draft')

    def update_name(self):
        # crd = self.id
        # records = self.env['project.activity.type'].search([('project_actn_id','=',crd)])
        # _logger.info("-----1----message-player_id--------,%s",records)
        # if self.realname:
        #     self.name = self.realname
        #     records.name = self.realname
        #     self.status = 'done'

        return True

class ProjectActivityTypeNameLine(models.Model):
    _name = 'project.activity.type.name.line'
    _description = "ProjectActivityTypeNameLine"

    
 
    name = fields.Char("Name")
    patn_id = fields.Many2one('project.activity.type.name','Activity Type Name')
    checklist_id = fields.Many2one('project.checklist.template','Checklist')