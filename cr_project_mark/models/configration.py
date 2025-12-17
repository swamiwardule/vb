# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class ProjectChecklistTemplate(models.Model):
    _inherit = 'project.checklist.template'

    marks = fields.Integer('Marks')


class ProjectChecklistLine(models.Model):
    _inherit = 'project.checklist.line'

    checklist_mark = fields.Integer(related='checklist_template_id.marks')


class ProjectActivityType(models.Model):
    _inherit = 'project.activity.type'

    act_type_rating = fields.Float('Rating')
    # total_act_type_rate = fields.Float('Total Rating')
    # obt_act_type_rate = fields.Float('Obtain Rating')

    def type_progress_rating(self):
        _logger.info(
            "==============type_progress_rating is called===============")
        activity_types = self.search([('checklist_ids', '!=', False), (
            'checklist_ids.checklist_mark', '>', 0), ('checklist_ids.is_pass', 'in', ['yes', 'nop'])])
        # _logger.info(
        #     "========activity_types===================%s", activity_types)

        updated_activity = []
        for rec in activity_types:
            rec.act_type_rating = 0
            checklist_ids = rec.checklist_ids
            total_rate = sum(checklist_ids.mapped('checklist_mark'))
            # _logger.info("===========total_rate===========%s", total_rate)
            obtain_rate = sum(checklist_ids.filtered(
                lambda x: x.is_pass in ['yes', 'nop']).mapped('checklist_mark'))
            # _logger.info(
            #     "================obtain_rate====================%s", obtain_rate)
            if total_rate and obtain_rate:
                rec.act_type_rating = (obtain_rate / total_rate) * 10

                updated_activity.append(rec.activity_id.id)
                # _logger.info(
                #     "============act_type_rating=========%s", updated_activity)
        if updated_activity:
            updated_activity_ids = self.env['project.activity'].browse(
                updated_activity)
            # _logger.info("===============ids=================%s",
            #  updated_activity_ids)
            updated_activity_ids.check_act_progress_rating()


class ProjectActivity(models.Model):
    _inherit = 'project.activity'

    act_rating = fields.Float('Rating')
    # total_act_rate = fields.Float('Total Rating')
    # obt_act_rate = fields.Float('Obtain Rating')

    def check_act_progress_rating(self):
        _logger.info(
            "===========check_act_progress_rating called ======================")

        updated_floors = []
        updated_flats = []
        for rec in self:
            rec.act_rating = 0
            activity_types = rec.activity_type_ids.filtered(
                lambda obj: obj.status not in ['draft', 'submit'])
            if activity_types:
                total_rate = len(activity_types) * 10
                obtain_rate = sum(activity_types.mapped('act_type_rating'))
                if total_rate and obtain_rate:
                    rec.act_rating = (obtain_rate / total_rate) * 10
                    updated_floors.append(rec.floor_id.id)
                    updated_flats.append(rec.flat_id.id)
        if updated_floors:
            updated_floors_ids = self.env['project.floors'].browse(
                updated_floors)
            updated_floors_ids.check_floors_progress_rating()
        if updated_flats:
            updated_flats_ids = self.env['project.flats'].browse(updated_flats)
            updated_flats_ids.check_flats_progress_rating()

    # def write(self, vals):
    #     res = super(ProjectActivity, self).write(vals)
    #     self.check_act_progress_rating()
    #     return res


class ProjectFloors(models.Model):
    _inherit = 'project.floors'

    floors_rating = fields.Float('Rating')
    # floors_total_rating = fields.Float('Total Rating')
    # floors_obt_rating = fields.Float('Obtain Rating')

    def check_floors_progress_rating(self):
        _logger.info(
            "===========check_floors_progress_rating ======================")
        updated_towers = []
        for rec in self:
            rec.floors_rating = 0
            activities = rec.activity_ids
            if activities:
                total_rate = len(activities.filtered(
                    lambda obj: obj.act_rating != 0.0)) * 10
                obt_rate = sum(activities.mapped('act_rating'))
                if total_rate and obt_rate:
                    rec.floors_rating = (obt_rate / total_rate) * 10
                    updated_towers.append(rec.tower_id.id)
        if updated_towers:
            updated_towers_ids = self.env['project.tower'].browse(
                updated_towers)
            updated_towers_ids.check_tower_progress_rating()

    # def write(self, vals):
    #     res = super(ProjectFloors, self).write(vals)
    #     self.check_floors_progress_rating()
    #     return res


class ProjectFlats(models.Model):
    _inherit = 'project.flats'

    flats_rating = fields.Float('Rating')
    # flats_total_rating = fields.Float('Total Rating')
    # flats_obt_rating = fields.Float('Obtain Rating')

    def check_flats_progress_rating(self):
        _logger.info(
            "===========check_flat_progress_rating ======================")
        updated_towers = []
        for rec in self:
            rec.flats_rating = 0
            activities = rec.activity_ids
            if activities:
                total_rate = len(activities.filtered(
                    lambda obj: obj.act_rating != 0.0)) * 10
                obt_rate = sum(activities.mapped('act_rating'))
                if total_rate and obt_rate:
                    rec.flats_rating = (obt_rate / total_rate) * 10
                    updated_towers.append(rec.tower_id.id)
        if updated_towers:
            updated_towers_ids = self.env['project.tower'].browse(
                updated_towers)
            updated_towers_ids.check_tower_progress_rating()
    # def write(self, vals):
    #     res = super(ProjectFlats, self).write(vals)
    #     self.check_flats_progress_rating()
    #     return res


class ProjectTower(models.Model):
    _inherit = 'project.tower'

    tower_rating = fields.Float('Rating')
    # tower_total_rating = fields.Float('Rating')
    # tower_obt_rating = fields.Float('Rating')

    def check_tower_progress_rating(self):
        # _logger.info(
        #     "-=================check_tower_progress_rating========is called")
        updated_projects = []
        for rec in self:
            rec.tower_rating = 0
            tower_floor_line_id = rec.tower_floor_line_id
            tower_flat_line_id = rec.tower_flat_line_id
            if tower_floor_line_id or tower_flat_line_id:
                obt_rate = sum(tower_floor_line_id.mapped(
                    'floors_rating')) + sum(tower_flat_line_id.mapped('flats_rating'))
                total_len = len(tower_floor_line_id.filtered(lambda obj: obj.floors_rating != 0.0)) + \
                    len(tower_flat_line_id.filtered(
                        lambda obj: obj.flats_rating != 0.0))
                total_rate = total_len * 10
                if obt_rate and total_rate:
                    rec.tower_rating = (obt_rate / total_rate) * 10
                    updated_projects.append(rec.project_id.id)
        if updated_projects:
            updated_projects_ids = self.env['project.info'].browse(
                updated_projects)
            updated_projects_ids.check_project_progress_rating()

    # def write(self, vals):
    #     res = super(ProjectTower, self).write(vals)
    #     self.check_tower_progress_rating()
    #     return res


class ProjectInfoTowerLineTemp(models.Model):
    _inherit = 'project.info.tower.line.temp'

    project_tower_rating = fields.Float(related='tower_id.tower_rating')
    # pro_tower_total_rating = fields.Float(related='tower_id.tower_total_rating')
    # pro_tower_obt_rating = fields.Float(related='tower_id.tower_obt_rating')

    # def check_project_tower_progress_rating(self):
    #     for rec in self:
    #         rec.project_tower_rating = 0
    #         rec.pro_tower_total_rating = 0
    #         rec.pro_tower_obt_rating = 0
    #         if rec.tower_id.tower_floor_line_id or rec.tower_id.tower_flat_line_id:
    #             obt_rate = sum(rec.tower_id.tower_floor_line_id.mapped('floors_obt_rating')) + sum(
    #                 rec.tower_id.tower_flat_line_id.mapped('flats_obt_rating'))
    #             total_rate = sum(rec.tower_id.tower_floor_line_id.mapped('floors_total_rating')) + sum(
    #                 rec.tower_id.tower_flat_line_id.mapped('flats_total_rating'))
    #             rec.project_tower_rating = (obt_rate / total_rate) * 10
    #             rec.pro_tower_total_rating = obt_rate
    #             rec.pro_tower_obt_rating = total_rate


class ProjectInfo(models.Model):
    _inherit = 'project.info'

    project_rating = fields.Float(string="Rating")
    # project_total_rating = fields.Float(string="Total Rating")
    # project_obt_rating = fields.Float(string="Obtain Rating")

    def check_project_progress_rating(self):
        _logger.info("=========check_project_rating=================is called")
        for rec in self:
            rec.project_rating = 0
            project_info_tower_line_temp = rec.project_info_tower_line_temp
            if project_info_tower_line_temp:
                total_rate = len(project_info_tower_line_temp.filtered(
                    lambda obj: obj.project_tower_rating != 0.0)) * 10
                obt_rate = sum(project_info_tower_line_temp.mapped(
                    'project_tower_rating'))
                if obt_rate and total_rate:
                    rec.project_rating = (obt_rate / total_rate) * 10

    # def write(self, vals):
    #     res = super(ProjectInfo, self).write(vals)
    #     self.check_project_progress_rating()
    #     return res
