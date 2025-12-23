# -*- coding: utf-8 -*-
import json
import requests
import matplotlib.pyplot as plt
import io
import base64
from odoo import tools
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ManuallySetFlagWizard(models.TransientModel):
    _name = 'manually.set.flag.wizard'
    _description = 'Manually Set Flag wizard'

    image = fields.Binary('Image')
    filename = fields.Char('File name')
    description = fields.Text("Description")


    def submit_flag(self):
        print('33333')
        self.write({'status': 'submit'})

    def close_flag(self):
        active_model = self._context['active_model']
        active_id = self._context['active_id']
        manually_flag_id = self.env[active_model].browse(active_id)
        if self.description and self.image:
            manually_flag_id.write(
                {'description': self.description, 'image': self.image, 'status': 'close'})


class ManuallySetFlag(models.Model):
    _name = 'manually.set.flag'
    _description = "ManuallySetFlag"

    project_info_id = fields.Many2one('project.info')
    project_tower_id = fields.Many2one('project.tower', ondelete='set null')
    project_floor_id = fields.Many2one('project.floors')
    project_flats_id = fields.Many2one('project.flats')
    # project_activity_id = fields.Many2one('project.activity')
    # project_act_type_id = fields.Many2one('project.activity.type')
    # project_check_line_id = fields.Many2one('project.checklist.line')
    project_activity_id = fields.Many2one('project.activity.name')
    project_act_type_id = fields.Many2one(
        'project.activity.name.line',  string="Activity Type Line")
    project_check_line_id = fields.Many2one(
        'project.activity.type.name.line', string="Checklist Line"
    )
    project_create_date = fields.Datetime('Date')
    project_responsible = fields.Many2one('res.users',string='Project Responsible', domain=lambda self: [('groups_id', 'in', self.env.ref('custom_project_management.group_quality_maker').id)]) 
    # cre_nc = fields.Integer('NC', readonly=True)
    # cre_yellow = fields.Integer('Yellow Flag', readonly=True)
    # cre_orange = fields.Integer('Orange Flag', readonly=True)
    # cre_red = fields.Integer('Red Flag', readonly=True)
    # cre_Green = fields.Integer('Green Flag', readonly=True)
    cre_nc = fields.Integer(compute="_compute_flag_counts", store=True)
    cre_yellow = fields.Integer(compute="_compute_flag_counts", store=True)
    cre_orange = fields.Integer(compute="_compute_flag_counts", store=True)
    cre_red = fields.Integer(compute="_compute_flag_counts", store=True)
    cre_Green = fields.Integer(compute="_compute_flag_counts", store=True)

    is_created = fields.Boolean(default=False)
    status = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('submit','Submit'),     
                              ('close', 'Close'),('approver_reject', 'Approver Rejected')], string="Status", default='draft')

    rectified_image = fields.Binary('Rectified File')
    filename = fields.Char("filename")
    description = fields.Text("Checker/Approver Remarks")
    overall_remarks = fields.Text("Maker Remark")
    approver_remark = fields.Text("Approver Remark")
    flag_category = fields.Selection([('Nc', 'NC'), ('Yellow Flag', 'Yellow Flag'), (
        'Orange Flag', 'Orange Flag'), ('Red Flag', 'Red Flag'), ('Green Flag', 'Green Flag')], string="Flag Category")
    seq_number = fields.Char('Sequence Number', readonly=True, required=True, copy=False, index=True,
                             default=lambda self: _('New'))
    pie_chart_image = fields.Binary("Pai Chart Image", attachment=True)
    bar_chart_image = fields.Binary("Bar Chart Image", attachment=True)
    chart_image_filename = fields.Char("Chart Image Filename")
    combined_chart_image = fields.Binary("Combined Chart Image", readonly=True)
    project_rating = fields.Float(
        string="Rating", compute='_compute_project_rating', store=True)
    # image_id = fields.Many2one('project.checklist.line.images',
    #                            compute="_compute_image", string="Image", store=True)
    image_id = fields.Many2one('project.checklist.line.images')
    image = fields.Binary(string="Image")
    image_x = fields.Binary("Photo", store=True)
    # image_x = fields.Binary("Photo", compute="_compute_image", store=True)

    custom_checklist_item = fields.Text(string='Custom Checklist Item')
   
   # for saving 5 images
    image_ids = fields.One2many('manually.set.flag.images', 'flag_id', string="Images")
    rectified_image_ids = fields.One2many('manually.set.flag.rectified.images', 'flag_id', string="Rectified Images")
    approver_image_ids = fields.One2many(
        'manually.set.flag.close.images',
        'flag_id',
        string="Close Images"
    )
    approver_close_image_ids = fields.One2many(
        'manually.set.flag.approver.close.images',
        'flag_id',
        string="Approver Close Images"
    )

    @api.depends('flag_category', 'status')
    def _compute_flag_counts(self):
        for rec in self:
            # Reset all counts
            rec.cre_nc = 0
            rec.cre_yellow = 0
            rec.cre_orange = 0
            rec.cre_red = 0
            rec.cre_Green = 0

            # Count ONLY if NOT closed
            if rec.status != 'close':
                if rec.flag_category == 'Nc':
                    rec.cre_nc = 1
                elif rec.flag_category == 'Yellow Flag':
                    rec.cre_yellow = 1
                elif rec.flag_category == 'Orange Flag':
                    rec.cre_orange = 1
                elif rec.flag_category == 'Red Flag':
                    rec.cre_red = 1
                elif rec.flag_category == 'Green Flag':
                    rec.cre_Green = 1


    @api.constrains('image_ids', 'rectified_image_ids', 'approver_image_ids','approver_close_image_ids')
    def _check_max_5_images(self):
        for record in self:
            if len(record.image_ids) > 5:
                raise ValidationError("You can upload a maximum of 5 images only.")
            if len(record.rectified_image_ids) > 5:
                raise ValidationError("You can upload a maximum of 5 rectified images only.")
            if len(record.approver_image_ids) > 5:
                raise ValidationError("You can upload a maximum of 5 close images only.")
            if len(record.approver_close_image_ids) > 5:
                raise ValidationError("You can upload a maximum of 5 approver close images only.")

    @api.model
    def create(self, vals):
        _logger.info("Before setting sequence: %s", vals)

        if vals.get('seq_number', _('New')) == _('New'):
            seq = self.env['ir.sequence'].next_by_code(
                'manually.set.flag') or _('New')
            vals['seq_number'] = seq

        _logger.info("After setting sequence: %s", vals)

        return super(ManuallySetFlag, self).create(vals)
  # changed code _ 23-01-2025

    # @api.onchange('project_check_line_id')
    # def _compute_image(self):
    #     if self.project_check_line_id and self.project_check_line_id.image_id:
    #         image_ids = self.project_check_line_id.image_id.ids
    #         if image_ids:
    #             image_record = self.env['project.checklist.line.images'].browse(
    #                 image_ids[0])
    #             self.image_id = image_record.id
    #             self.image = image_record.image if image_record.image else None
    #             print('=================Image========',
    #                   image_record, self.image_id, self.image)

    @api.depends('project_info_id')
    def _compute_project_rating(self):
        for rec in self:
            if rec.project_info_id:
                rec.project_rating = rec.project_info_id.project_rating

    def download_image(self):
        fieldname = self._context.get('fieldname')
        if fieldname:
            return {
                'name': 'Image',
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=manually.set.flag&id=" + str(self.id) + "&filename_field=filename&field=" + fieldname + "&download=true&filename=Image",
                'target': 'self',
            }

    def create_flag_counter_manually(self):
        for rec in self:
            # if rec.project_check_line_id and rec.is_created == False:
            if rec.project_check_line_id and not rec.is_created:
                rec.project_check_line_id.project_line_nc += rec.cre_nc
                rec.project_check_line_id.project_line_yellow += rec.cre_yellow
                rec.project_check_line_id.project_line_orange += rec.cre_orange
                rec.project_check_line_id.project_line_red += rec.cre_red
                rec.project_check_line_id.project_line_green += rec.cre_Green
                rec.is_created = True


    def submit_flag(self):
        print('33333')
        self.write({'status': 'submit'})


    def close_flag(self):
        print('33333')
        self.write({'status': 'close'})

    def open_flag(self):
        print('33333')
        self.write({'status': 'open'})

    def get_approvers_for_nc(self):
        """
        Returns list of users who are in Approver group 
        AND assigned to the same project & tower.
        """
        approver_users = []
        approver_group = self.env.ref("custom_project_management.group_approver")

        for user in self.project_tower_id.assigned_to_ids:
            if approver_group in user.groups_id:
                approver_users.append(user)
        
        return approver_users

    @api.model
    def get_report_data(self, docids):
        """Optimized method to fetch report data with all relationships"""
        
        _logger.info('Fetching report data for %s records', len(docids))
        
        # Get records
        docs = self.browse(docids)
        
        # Pre-fetch all related fields to avoid multiple queries during rendering
        # This is crucial for performance
        docs.mapped('project_info_id.name')
        docs.mapped('project_tower_id.name')
        docs.mapped('project_floor_id.name')
        docs.mapped('project_flats_id.name')
        docs.mapped('project_activity_id.name')
        docs.mapped('project_act_type_id.name')
        
        # Pre-fetch images - MOST IMPORTANT
        # This loads all images in bulk instead of one-by-one
        docs.mapped('project_check_line_id.image_ids.image')
        docs.mapped('project_check_line_id.image_ids.filename')
        docs.mapped('rectified_image_ids.rectified_image')
        docs.mapped('rectified_image_ids.filename')
        docs.mapped('image')
        docs.mapped('filename')
        
        _logger.info('Report data fetching completed')
        
        return docs




    # def send_notification(self):
    #     """ Sends push notification to the responsible person """
    #     if not self.project_responsible:
    #         return {'error': 'No responsible person assigned'}

    #     project_name = self.project_info_id.name if self.project_info_id else 'Unknown Project'
    #     tower_name = self.project_tower_id.name if self.project_tower_id else 'Unknown Tower'

    #     message = f"A {self.flag_category} has been created for {project_name}, Tower: {tower_name}."
    #     title = "New NC Created"

    #     # Get Push Notification ID
    #     player_id, user_r = self.env['res.users'].sudo(
    #     ).get_player_id(self.project_responsible.id)
    #     player_ids = [player_id] if player_id else []

    #     if not player_ids:
    #         return {'error': 'No push notification ID found for the responsible person'}

    #     # OneSignal API credentials
    #     app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
    #     rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

    #     # Data to send in the notification
    #     data = {
    #         "app_id": app_id,
    #         "include_player_ids": player_ids,
    #         "contents": {"en": message},
    #         "headings": {"en": title},
    #     }

    #     # Convert data to JSON
    #     data_json = json.dumps(data)

    #     # URL for OneSignal REST API
    #     url = "https://onesignal.com/api/v1/notifications"

    #     # Headers for the request
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Basic {rest_api_key}"
    #     }

    #     # Send the notification
    #     response = requests.post(url, data=data_json, headers=headers)

    #     # Log Notification Status
    #     status = 'sent' if response.status_code == 200 else 'failed'
    #     self.env['app.notification.log'].sudo().create({
    #         'title': title if status == 'sent' else f"{title} (Failed)",
    #         'message': message,
    #         'res_user_id': self.project_responsible.id,
    #         'player_id': player_id,
    #         'status': status,
    #         'table_id': self.id,
    #         'project_info_id': self.project_info_id.id if self.project_info_id else False,
    #         'tower_id': self.project_tower_id.id if self.project_tower_id else False,
    #     })
    #     _logger.info("=======notification====================")

    #     return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}


# added - 18-3
    """Scheduled action to check flag category progression when checklist is rejected"""
    # @api.model
    # def auto_update_flags(self):
    #     _logger.info("======auto_update_flags=====")
    #     """Scheduled action to check flag category progression when checklist is rejected"""
    #     today = fields.Datetime.now()
    #     flags = self.search([('status', '!=', 'close')])
    #     _logger.info(
    #         "Scheduled action to check flag category progression is called")
    #     for flag in flags:
    #         days_elapsed = (today - flag.create_date).days

    #         # if flag.project_check_line_id and flag.project_check_line_id.checklist_id.is_pass == 'no':
    #             if flag.flag_category == 'nc' and days_elapsed >= 2:
    #                 flag.write({'flag_category': 'yellow'})
    #             elif flag.flag_category == 'yellow' and days_elapsed >= 7:
    #                 flag.write({'flag_category': 'orange'})
    #             elif flag.flag_category == 'orange' and days_elapsed >= 14:
    #                 flag.write({'flag_category': 'red'})

    # @api.onchange('flag_category')
    # def _onchange_flag_category(self):
    #     if self.flag_category == 'Nc':
    #         self.cre_nc = (self.cre_nc or 0) + 1
    #     elif self.flag_category == 'Yellow Flag':
    #         self.cre_yellow = (self.cre_yellow or 0) + 1
    #     elif self.flag_category == 'Orange Flag':
    #         self.cre_orange = (self.cre_orange or 0) + 1
    #     elif self.flag_category == 'Red Flag':
    #         self.cre_red = (self.cre_red or 0) + 1
    #     elif self.flag_category == 'Green Flag':
    #         self.cre_Green = (self.cre_Green or 0) + 1

    # @api.model
    # def create(self, vals):
    #     if 'flag_category' in vals:
    #         if vals['flag_category'] == 'Nc' and not vals.get('cre_nc'):
    #             vals['cre_nc'] = 1
    #         elif vals['flag_category'] == 'Yellow Flag' and not vals.get('cre_yellow'):
    #             vals['cre_yellow'] = 1
    #         elif vals['flag_category'] == 'Orange Flag' and not vals.get('cre_orange'):
    #             vals['cre_orange'] = 1
    #         elif vals['flag_category'] == 'Red Flag' and not vals.get('cre_red'):
    #             vals['cre_red'] = 1
    #         elif vals['flag_category'] == 'Green Flag' and not vals.get('cre_Green'):
    #             vals['cre_Green'] = 1
    #     return super().create(vals)

    @api.model
    def create(self, vals):
        if vals.get('seq_number', _('New')) == _('New'):
            vals['seq_number'] = self.env['ir.sequence'].next_by_code('manually.set.flag') or _('New')

        # ✅ Count only if NOT closed
        if vals.get('status', 'draft') != 'close':
            category = vals.get('flag_category')
            if category == 'Nc':
                vals['cre_nc'] = 1
            elif category == 'Yellow Flag':
                vals['cre_yellow'] = 1
            elif category == 'Orange Flag':
                vals['cre_orange'] = 1
            elif category == 'Red Flag':
                vals['cre_red'] = 1
            elif category == 'Green Flag':
                vals['cre_Green'] = 1

        return super().create(vals)


    # def write(self, vals):
    #     for rec in self:
    #         if 'flag_category' in vals:
    #             if vals['flag_category'] == 'Nc':
    #                 vals['cre_nc'] = (rec.cre_nc or 0) + 1
    #             elif vals['flag_category'] == 'Yellow Flag':
    #                 vals['cre_yellow'] = (rec.cre_yellow or 0) + 1
    #             elif vals['flag_category'] == 'Orange Flag':
    #                 vals['cre_orange'] = (rec.cre_orange or 0) + 1
    #             elif vals['flag_category'] == 'Red Flag':
    #                 vals['cre_red'] = (rec.cre_red or 0) + 1
    #             elif vals['flag_category'] == 'Green Flag':
    #                 vals['cre_Green'] = (rec.cre_Green or 0) + 1
    #     return super().write(vals)  

    def write(self, vals):
        for rec in self:

            # ⛔ Do nothing if flag already closed
            if rec.status == 'close':
                continue

            # ✅ If user is closing the flag → do NOT count
            if vals.get('status') == 'close':
                continue

            # ✅ Count only when category changes AND flag is not closed
            if 'flag_category' in vals:
                category = vals['flag_category']

                if category == 'Nc':
                    vals['cre_nc'] = (rec.cre_nc or 0) + 1
                elif category == 'Yellow Flag':
                    vals['cre_yellow'] = (rec.cre_yellow or 0) + 1
                elif category == 'Orange Flag':
                    vals['cre_orange'] = (rec.cre_orange or 0) + 1
                elif category == 'Red Flag':
                    vals['cre_red'] = (rec.cre_red or 0) + 1
                elif category == 'Green Flag':
                    vals['cre_Green'] = (rec.cre_Green or 0) + 1

        return super().write(vals)
 
    
    def scheduler_update_flags(self):
        today = fields.Date.today()

        records = self.search([('status', '!=', 'close')])

        for rec in records:
            if not rec.project_create_date:
                continue

            project_date = rec.project_create_date.date() if isinstance(rec.project_create_date, datetime) else rec.project_create_date
            days = (today - project_date).days

            # 1️⃣ Auto-create NC ONLY IF there is NO flag assigned yet
            if rec.flag_category in (False, 'None', '', None) and days >= 2:
                rec.write({
                    'flag_category': 'Nc',
                    'project_create_date': today,
                    'cre_nc': rec.cre_nc + 1
                })
                continue

            # 2️⃣ NC → Yellow (after 4 days)
            if rec.flag_category == 'Nc' and days >= 4:
                rec.write({
                    'flag_category': 'Yellow Flag',
                    'project_create_date': today
                })
                continue

            # 3️⃣ Yellow → Orange (after 7 days)
            if rec.flag_category == 'Yellow Flag' and days >= 7:
                rec.write({
                    'flag_category': 'Orange Flag',
                    'project_create_date': today
                })
                continue

            # 4️⃣ Orange → Red (after 14 days)
            if rec.flag_category == 'Orange Flag' and days >= 14:
                rec.write({
                    'flag_category': 'Red Flag',
                    'project_create_date': today
                })
                continue


    # Update ONLY these two classes in your existing models.py file

class ManuallySetFlagImages(models.Model):
    _name = 'manually.set.flag.images'
    _description = 'Flag Images'
    _rec_name = 'filename'
    _order = 'sequence, id'

    flag_id = fields.Many2one('manually.set.flag', string="Flag Reference", ondelete='cascade', required=True)
    image = fields.Binary('Image', required=True, attachment=True)
    filename = fields.Char('File Name', default='image.jpg', required=True)
    mimetype = fields.Char('MIME Type', compute='_compute_mimetype', store=True)
    checksum = fields.Char('Checksum')
    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now, readonly=True)
    description = fields.Char(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)

    @api.depends('filename')
    def _compute_mimetype(self):
        """Compute MIME type based on file extension"""
        mime_mapping = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        for record in self:
            if record.filename:
                ext = record.filename[record.filename.rfind('.'):].lower() if '.' in record.filename else ''
                record.mimetype = mime_mapping.get(ext, 'image/jpeg')
            else:
                record.mimetype = 'image/jpeg'

    @api.model
    def create(self, vals):
        """Ensure filename always has a proper value"""
        if not vals.get('filename') or not vals.get('filename', '').strip():
            vals['filename'] = f"image_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        elif '.' not in vals.get('filename', ''):
            vals['filename'] = f"{vals.get('filename')}.jpg"
        return super(ManuallySetFlagImages, self).create(vals)

    def write(self, vals):
        """Ensure filename always has a proper value on update"""
        if 'filename' in vals:
            if not vals['filename'] or not vals['filename'].strip():
                vals['filename'] = f"image_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            elif '.' not in vals['filename']:
                vals['filename'] = f"{vals['filename']}.jpg"
        return super(ManuallySetFlagImages, self).write(vals)


class ManuallySetFlagRectifiedImages(models.Model):
    _name = 'manually.set.flag.rectified.images'
    _description = 'Flag Rectified Images'
    _rec_name = 'filename'
    _order = 'sequence, id'

    flag_id = fields.Many2one('manually.set.flag', string="Flag Reference", ondelete='cascade', required=True)
    rectified_image = fields.Binary('Image', required=True, attachment=True)
    filename = fields.Char('File Name', default='image.jpg', required=True)
    mimetype = fields.Char('MIME Type', compute='_compute_mimetype', store=True)
    checksum = fields.Char('Checksum')
    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now, readonly=True)
    description = fields.Char(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    rectified_by = fields.Many2one('res.users', string='Rectified By', default=lambda self: self.env.user, readonly=True)
    rectified_date = fields.Date(string='Rectified Date', default=fields.Date.today, readonly=True)

    @api.depends('filename')
    def _compute_mimetype(self):
        """Compute MIME type based on file extension"""
        mime_mapping = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        for record in self:
            if record.filename:
                ext = record.filename[record.filename.rfind('.'):].lower() if '.' in record.filename else ''
                record.mimetype = mime_mapping.get(ext, 'image/jpeg')
            else:
                record.mimetype = 'image/jpeg'

    @api.model
    def create(self, vals):
        """Ensure filename always has a proper value"""
        if not vals.get('filename') or not vals.get('filename', '').strip():
            vals['filename'] = f"rectified_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        elif '.' not in vals.get('filename', ''):
            vals['filename'] = f"{vals.get('filename')}.jpg"
        return super(ManuallySetFlagRectifiedImages, self).create(vals)

    def write(self, vals):
        """Ensure filename always has a proper value on update"""
        if 'filename' in vals:
            if not vals['filename'] or not vals['filename'].strip():
                vals['filename'] = f"rectified_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            elif '.' not in vals['filename']:
                vals['filename'] = f"{vals['filename']}.jpg"
        return super(ManuallySetFlagRectifiedImages, self).write(vals)

class ManuallySetFlagCloseImages(models.Model):
    _name = 'manually.set.flag.close.images'
    _description = 'Flag Close Images'
    _rec_name = 'filename'
    _order = 'sequence, id'

    flag_id = fields.Many2one(
        'manually.set.flag',
        string="Flag Reference",
        ondelete='cascade',
        required=True
    )

    approver_image = fields.Binary(
        'Approver Reject Image',
        required=True,
        attachment=True
    )

    filename = fields.Char(
        'File Name',
        default='approver_image.jpg',
        required=True
    )

    mimetype = fields.Char(
        'MIME Type',
        compute='_compute_mimetype',
        store=True
    )

    upload_date = fields.Datetime(
        string='Upload Date',
        default=fields.Datetime.now,
        readonly=True
    )

    description = fields.Char('Description')

    sequence = fields.Integer(default=10)

    closed_by = fields.Many2one(
        'res.users',
        string='Closed By',
        default=lambda self: self.env.user,
        readonly=True
    )

    closed_date = fields.Date(
        string='Closed Date',
        default=fields.Date.today,
        readonly=True
    )

    # ---------- helpers ----------
    @api.depends('filename')
    def _compute_mimetype(self):
        mime_mapping = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        for rec in self:
            if rec.filename and '.' in rec.filename:
                ext = rec.filename[rec.filename.rfind('.'):].lower()
                rec.mimetype = mime_mapping.get(ext, 'image/jpeg')
            else:
                rec.mimetype = 'image/jpeg'

    @api.model
    def create(self, vals):
        if not vals.get('filename') or not vals['filename'].strip():
            vals['filename'] = f"close_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        elif '.' not in vals['filename']:
            vals['filename'] = f"{vals['filename']}.jpg"
        return super().create(vals)
    
class ManuallySetFlagApproverCloseImages(models.Model):
    _name = 'manually.set.flag.approver.close.images'
    _description = 'Flag Approver Close Images'
    _rec_name = 'filename'
    _order = 'sequence, id'

    flag_id = fields.Many2one(
        'manually.set.flag',
        string="Flag Reference",
        ondelete='cascade',
        required=True
    )

    approver_close_img = fields.Binary(
        'Approver Close Image',
        required=True,
        attachment=True
    )

    filename = fields.Char(
        'File Name',
        default='approver_close.jpg',
        required=True
    )

    mimetype = fields.Char(
        'MIME Type',
        compute='_compute_mimetype',
        store=True
    )

    upload_date = fields.Datetime(
        string='Upload Date',
        default=fields.Datetime.now,
        readonly=True
    )

    description = fields.Char('Description')

    sequence = fields.Integer(default=10)

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        default=lambda self: self.env.user,
        readonly=True
    )

    approved_date = fields.Date(
        string='Approved Date',
        default=fields.Date.today,
        readonly=True
    )

    # ---------- helpers ----------
    @api.depends('filename')
    def _compute_mimetype(self):
        mime_mapping = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
        }
        for rec in self:
            if rec.filename and '.' in rec.filename:
                ext = rec.filename[rec.filename.rfind('.'):].lower()
                rec.mimetype = mime_mapping.get(ext, 'image/jpeg')
            else:
                rec.mimetype = 'image/jpeg'

    @api.model
    def create(self, vals):
        if not vals.get('filename'):
            vals['filename'] = f"approver_close_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        return super().create(vals)



class ReportManuallySetFlag(models.AbstractModel):
    """Custom report model for optimized rendering"""
    _name = 'report.set.flag.status'
    _description = 'Manually Set Flag Report'
    _auto = False  # prevents Odoo from creating a DB table

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info('Preparing report values for %s records', len(docids) if docids else 0)

        ManuallySetFlag = self.env['manually.set.flag']
        docs = ManuallySetFlag.browse(docids)
        try:
            docs.mapped('project_info_id.name')
            docs.mapped('project_tower_id.name')
            docs.mapped('project_floor_id.name')
            docs.mapped('project_flats_id.name')
            docs.mapped('project_activity_id.name')
            docs.mapped('project_act_type_id.name')
            docs.mapped('project_check_line_id.image_ids.image')
            docs.mapped('rectified_image_ids.rectified_image')
            docs.mapped('image')
        except Exception as e:
            _logger.error('Error during report data pre-fetch: %s', str(e))

        return {
            'doc_ids': docids,
            'doc_model': 'manually.set.flag',
            'docs': docs,
            'data': data,
        }


class ReportManuallySetFlagStatus(models.AbstractModel):
    """Custom report model for graph report"""
    _name = 'report.set.flag.status_status'
    _description = 'Manually Set Flag Status Report'
    _auto = False  # prevents Odoo from creating a DB table

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info('Preparing graph report for %s records', len(docids) if docids else 0)

        docs = self.env['manually.set.flag'].browse(docids)
        docs.mapped('pie_chart_image')
        docs.mapped('combined_chart_image')
        docs.mapped('bar_chart_image')
        docs.mapped('project_info_id.name')

        return {
            'doc_ids': docids,
            'doc_model': 'manually.set.flag',
            'docs': docs,
            'data': data,
        }





class ReportWizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    project_info_id = fields.Many2one('project.info', string="Project Info")
    project_tower_id = fields.Many2one('project.tower', string="Project Tower")
    status = fields.Selection([
        ('all', 'All'),
        ('open', 'Open'),
        ('close', 'Close')
    ], string="Status", default='all')

    from_date = fields.Date('From Date')
    to_date = fields.Date()

    def _get_default_records(self):
        active_ids = self.env.context.get('active_ids', [])
        return [(6, 0, active_ids)]

    record_ids = fields.Many2many(
        'manually.set.flag', default=_get_default_records)

    def _get_domain(self):
        domain = []
        if self.project_info_id:
            domain.append(('project_info_id', '=', self.project_info_id.id))
        if self.project_tower_id:
            domain.append(('project_tower_id', '=', self.project_tower_id.id))
        if self.status != 'all':
            domain.append(('status', '=', self.status))
        if self.from_date:
            domain.append(('project_create_date', '>=', self.from_date))
        if self.to_date:
            domain.append(('project_create_date', '<=', self.to_date))
        _logger.info('Report Domain: %s', domain)
        return domain

    def _get_status_data(self, records):
        status_data = {
            'open': 0,
            'close': 0
        }
        for record in records:
            if record.status in status_data:
                status_data[record.status] += 1
        return status_data

    def _generate_combined_chart(self, status_data):
        colors = {
            'open': '#FF7F7F',
            'close': 'green'
        }

        # Generate Combined Bar Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        labels = list(status_data.keys())
        sizes = list(status_data.values())
        bars = ax.bar(labels, sizes, color=[colors[label] for label in labels])
        ax.set_xlabel('Status')
        ax.set_ylabel('Count')
        ax.set_title('Overall Status Count for All Projects')

        # Add data labels above each bar
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0,
                    yval + 0.5, str(yval), ha='center')

        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png')
        chart_buffer.seek(0)
        combined_chart_image = base64.b64encode(
            chart_buffer.read()).decode('ascii')
        chart_buffer.close()
        plt.close(fig)  # Close figure to free memory

        return combined_chart_image

    def _generate_charts(self, project_name, status_data):
        # Define colors for the charts
        colors = {
            'open': '#FF7F7F',
            'close': 'green'
        }

        # Generate Bar Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        labels = list(status_data.keys())
        sizes = list(status_data.values())
        bars = ax.bar(labels, sizes, color=[colors[label] for label in labels])
        ax.set_xlabel('Status')
        ax.set_ylabel('Count')
        ax.set_title(f'Project Status Count for {project_name}')

        # Add project name below each bar
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0,
                    yval + 0.5, project_name, ha='center')

        bar_chart_buffer = io.BytesIO()
        plt.savefig(bar_chart_buffer, format='png')
        bar_chart_buffer.seek(0)
        bar_chart_image = base64.b64encode(
            bar_chart_buffer.read()).decode('ascii')
        bar_chart_buffer.close()
        plt.close(fig)  # Close figure to free memory

        # Generate Pie Chart
        fig, ax = plt.subplots(figsize=(8, 6))
        labels = list(status_data.keys())
        sizes = list(status_data.values())
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=[
               colors[label] for label in labels], startangle=90)
        ax.axis('equal')

        pie_chart_buffer = io.BytesIO()
        plt.savefig(pie_chart_buffer, format='png')
        pie_chart_buffer.seek(0)
        pie_chart_image = base64.b64encode(
            pie_chart_buffer.read()).decode('ascii')
        pie_chart_buffer.close()
        plt.close(fig)  # Close figure to free memory

        return bar_chart_image, pie_chart_image

    def _get_status_data_combined(self, records):
        status_data = {
            'open': 0,
            'close': 0
        }
        for record in records:
            if record.status in status_data:
                status_data[record.status] += 1
        return status_data

    def generate_graph_report(self):
        domain = self._get_domain()
        records = self.env['manually.set.flag'].search(domain)

        if not records:
            raise UserError("No records found matching the criteria.")

        combined_status_data = self._get_status_data_combined(records)

        # Generate the combined chart for overall status counts
        combined_chart_image = self._generate_combined_chart(
            combined_status_data)

        project_status_data = {}
        for record in records:
            project_name = record.project_info_id.name
            if project_name not in project_status_data:
                project_records = records.filtered(
                    lambda r: r.project_info_id.name == project_name)
                project_status_data[project_name] = self._get_status_data(
                    project_records)

                for project_name, status_data in project_status_data.items():
                    bar_chart_image, pie_chart_image = self._generate_charts(
                        project_name, status_data)
                    record.pie_chart_image = pie_chart_image
                    record.bar_chart_image = bar_chart_image
                    record.combined_chart_image = combined_chart_image

        if records:
            return self.env.ref('custom_project_management.action_report_manually_graph_set_flag').report_action(
                docids=records[0]
            )

    def generate_report(self):
        """Generate PDF report with optimizations to prevent timeout"""
        self.ensure_one()
        
        domain = self._get_domain()
        
        # Get total count first
        total_count = self.env['manually.set.flag'].search_count(domain)
        
        _logger.info('Generating report for %s records', total_count)
        
        # Warning if too many records
        if total_count > 100:
            raise ValidationError(
                f"Too many records ({total_count}) found. This may cause timeout issues.\n\n"
                "Please narrow your search criteria:\n"
                "- Select a specific project\n"
                "- Choose a smaller date range\n"
                "- Filter by specific status\n\n"
                "Recommended: Maximum 100 records per report."
            )
        
        # if total_count == 0:
        #     raise UserError("No records found matching the criteria.")
        
        # Search with limit and order
        records = self.env['manually.set.flag'].search(
            domain, 
            order='project_create_date desc',
            limit=100
        )
        
        # Pre-fetch related fields in batch to optimize database queries
        # This prevents N+1 query problem
        try:
            _logger.info('Pre-fetching related fields...')
            
            # Prefetch all related fields at once
            records.mapped('project_info_id.name')
            records.mapped('project_tower_id.name')
            records.mapped('project_floor_id.name')
            records.mapped('project_flats_id.name')
            records.mapped('project_activity_id.name')
            records.mapped('project_act_type_id.name')
            
            # Prefetch images - this is the most important optimization
            records.mapped('project_check_line_id.image_ids.image')
            records.mapped('project_check_line_id.image_ids.filename')
            records.mapped('rectified_image_ids.rectified_image')
            records.mapped('rectified_image_ids.filename')
            records.mapped('image')
            records.mapped('filename')
            
            _logger.info('Pre-fetching completed successfully')
            
        except Exception as e:
            _logger.error('Error during pre-fetching: %s', str(e))
            # Continue even if prefetch fails
        
        # Generate report
        try:
            report = self.env.ref('custom_project_management.action_report_manually_set_flag')
            return report.report_action(records)
            
        except Exception as e:
            _logger.error('Error generating report: %s', str(e))
            raise UserError(
                f"Error generating report: {str(e)}\n\n"
                "Please try:\n"
                "1. Reducing the number of records\n"
                "2. Selecting fewer records with images\n"
                "3. Contacting your system administrator if the issue persists"
            )

    @api.constrains('from_date', 'to_date')
    def _check_dates(self):
        """Validate date range"""
        for wizard in self:
            if wizard.from_date and wizard.to_date:
                if wizard.from_date > wizard.to_date:
                    raise ValidationError("'From Date' cannot be later than 'To Date'.")