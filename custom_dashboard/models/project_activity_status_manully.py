# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import io
import base64
from odoo import tools
from odoo import models, fields, api, _


class ManuallySetFlagWizard(models.TransientModel):
    _name = 'manually.set.flag.wizard'
    _description = 'Manually Set Flag wizard'

    image = fields.Binary('Image')
    filename = fields.Char('File name')
    description = fields.Text("Description")

    def close_flag(self):
        active_model = self._context['active_model']
        active_id = self._context['active_id']
        manually_flag_id = self.env[active_model].browse(active_id)
        if self.description and self.image:
            manually_flag_id.write({'description': self.description, 'image': self.image, 'status': 'close'})


class ManuallySetFlag(models.Model):
    _name = 'manually.set.flag'
    _description = "ManuallySetFlag"

    project_info_id = fields.Many2one('project.info')
    project_tower_id = fields.Many2one('project.tower')
    project_floor_id = fields.Many2one('project.floors')
    project_flats_id = fields.Many2one('project.flats')
    project_activity_id = fields.Many2one('project.activity')
    project_act_type_id = fields.Many2one('project.activity.type')
    project_check_line_id = fields.Many2one('project.checklist.line')
    project_create_date = fields.Datetime('Date', default=lambda self: fields.Datetime.now())
    project_responsible = fields.Many2one('res.partner')
    cre_nc = fields.Integer('NC')
    cre_yellow = fields.Integer('Yellow Flag')
    cre_orange = fields.Integer('Orange Flag')
    cre_red = fields.Integer('Red Flag')
    cre_Green = fields.Integer('Green Flag')
    is_created = fields.Boolean(default=False)
    status = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('close', 'Close')], string="Status", default='draft')

    rectified_image = fields.Binary('Rectified File')
    filename = fields.Char("filename")
    description = fields.Text("Description")
    flag_category = fields.Selection([('nc','NC'),('yellow','Yellow Flag'),('orange','Orange Flag'),('red','Red Flag'),('green','Green Flag')],string="Flag Category")
    seq_number = fields.Char('Sequence Number', readonly=True, required=True, copy=False, index=True,
                             default=lambda self: _('New'))
    pie_chart_image = fields.Binary("Pai Chart Image", attachment=True)
    bar_chart_image = fields.Binary("Bar Chart Image", attachment=True)
    chart_image_filename = fields.Char("Chart Image Filename")
    combined_chart_image = fields.Binary("Combined Chart Image", readonly=True)
    project_rating = fields.Float(string="Rating", compute='_compute_project_rating', store=True)
    image_id = fields.Many2one('project.checklist.line.images', compute="_compute_image", string="Image", store=True)
    image = fields.Binary(string="Image", attachment=True, compute="_compute_image", store=True)
    image_x = fields.Binary("Photo", compute="_compute_image", store=True)

    @api.depends('project_check_line_id', 'description', 'image_id')
    def _compute_image(self):
        if self.project_check_line_id and self.project_check_line_id.image_ids:
            image_ids = self.project_check_line_id.image_ids.ids
            if image_ids:
                image_record = self.env['project.checklist.line.images'].browse(image_ids[0])
                image = self.env['project.checklist.line'].browse(self.project_check_line_id.id)
                # self.image_id = image_record.id
                self.write(
                    {'image_id': image_record.id, 'image': image.image if image.image else image.image})
                print('=================Image========', image_record, self.image_id, self.image, image.image)

    @api.depends('project_info_id')
    def _compute_project_rating(self):
        for rec in self:
            if rec.project_info_id:
                rec.project_rating = rec.project_info_id.project_rating

    @api.model
    def create(self, vals):
        if vals.get('seq_number', _('New')) == _('New'):
            seq = self.env['ir.sequence'].next_by_code('manually.set.flag') or _('New')
            vals['seq_number'] = seq
        return super(ManuallySetFlag, self).create(vals)

    def download_image(self):
        fieldname = self._context.get('fieldname')
        if fieldname:
            return {
                'name': 'Image',
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=manually.set.flag&id=" + str(self.id) + "&filename_field=filename&field=" + fieldname +"&download=true&filename=Image",
                'target': 'self',
            }

    def create_flag_counter_manually(self):
        for rec in self:
            if rec.project_check_line_id and rec.is_created == False:
                rec.project_check_line_id.project_line_nc += rec.cre_nc
                rec.project_check_line_id.project_line_yellow += rec.cre_yellow
                rec.project_check_line_id.project_line_orange += rec.cre_orange
                rec.project_check_line_id.project_line_red += rec.cre_Green
                rec.is_created = True

    def close_flag(self):
        print('33333')
        self.write({'status': 'close'})

    def open_flag(self):
        print('33333')
        self.write({'status': 'open'})


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

    from_date = fields.Date(
        'From Date')
    to_date = fields.Date()

    # default=lambda self: fields.Date.today())

    def _get_default_records(self):
        active_ids = self.env.context.get('active_ids', [])
        return [(6, 0, active_ids)]

    record_ids = fields.Many2many('manually.set.flag', default=_get_default_records)

    def _get_domain(self):
        domain = []
        if self.project_info_id:
            domain.append(('project_info_id', '=', self.project_info_id.id))
        if self.project_tower_id:
            domain.append(('project_tower_id', '=', self.project_tower_id.id))
        if self.status != 'all':
            domain.append(('status', '=', self.status))
        # else:
        #     domain.append(('status', 'in', ['open', 'close']))
        if self.from_date:
            domain.append(('project_create_date', '>=', self.from_date))
        if self.to_date:
            domain.append(('project_create_date', '<=', self.to_date))
        print('======domain=======', domain)
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

    # def _get_status_data(self, records):
    #     status_data = {
    #         'open': 0,
    #         'close': 0,
    #         # 'draft': 0
    #     }
    #     for record in records:
    #         status_data[record.status] = status_data.get(record.status, 0) + 1
    #     return status_data

    def _generate_combined_chart(self, status_data):
        colors = {
            'open': '#FF7F7F',  # Light red shade for 'open'
            'close': 'green'  # Keeping green for 'close'
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
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.5, str(yval), ha='center')

        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png')
        chart_buffer.seek(0)
        combined_chart_image = base64.b64encode(chart_buffer.read()).decode('ascii')
        chart_buffer.close()
        plt.clf()

        return combined_chart_image

    def _generate_charts(self, project_name, status_data):
        # Define colors for the charts
        colors = {
            # 'open': '#ffcccc',  # Light red shade for 'open'
            'open': '#FF7F7F',
            'close': 'green'  # Keeping green for 'close'
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
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.5, project_name, ha='center')

        bar_chart_buffer = io.BytesIO()
        plt.savefig(bar_chart_buffer, format='png')
        bar_chart_buffer.seek(0)
        bar_chart_image = base64.b64encode(bar_chart_buffer.read()).decode('ascii')
        bar_chart_buffer.close()
        plt.clf()  # Clear the current figure

        # Generate Pie Chart
        fig, ax = plt.subplots(figsize=(8, 6))
        labels = list(status_data.keys())
        sizes = list(status_data.values())
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=[colors[label] for label in labels], startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

        pie_chart_buffer = io.BytesIO()
        plt.savefig(pie_chart_buffer, format='png')
        pie_chart_buffer.seek(0)
        pie_chart_image = base64.b64encode(pie_chart_buffer.read()).decode('ascii')
        pie_chart_buffer.close()
        plt.clf()  # Clear the current figure

        return bar_chart_image, pie_chart_image

    # def _generate_charts(self, project_name, status_data):
    #     # Define colors for the charts
    #     colors = {
    #         'open': 'blue',
    #         'close': 'green'
    #     }
    #
    #     # Generate Bar Chart
    #     fig, ax = plt.subplots(figsize=(10, 6))
    #     labels = list(status_data.keys())
    #     sizes = list(status_data.values())
    #     bars = ax.bar(labels, sizes, color=[colors[label] for label in labels])
    #     ax.set_xlabel('Status')
    #     ax.set_ylabel('Count')
    #     ax.set_title(f'Project Status Count for {project_name}')
    #
    #     # Add project name below each bar
    #     for bar in bars:
    #         yval = bar.get_height()
    #         ax.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.5, project_name, ha='center')
    #
    #     bar_chart_buffer = io.BytesIO()
    #     plt.savefig(bar_chart_buffer, format='png')
    #     bar_chart_buffer.seek(0)
    #     bar_chart_image = base64.b64encode(bar_chart_buffer.read()).decode('ascii')
    #     bar_chart_buffer.close()
    #     plt.clf()  # Clear the current figure
    #
    #     # Generate Pie Chart
    #     fig, ax = plt.subplots(figsize=(8, 6))
    #     labels = list(status_data.keys())
    #     sizes = list(status_data.values())
    #     ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=[colors[label] for label in labels], startangle=90)
    #     ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    #
    #     pie_chart_buffer = io.BytesIO()
    #     plt.savefig(pie_chart_buffer, format='png')
    #     pie_chart_buffer.seek(0)
    #     pie_chart_image = base64.b64encode(pie_chart_buffer.read()).decode('ascii')
    #     pie_chart_buffer.close()
    #     plt.clf()  # Clear the current figure
    #
    #     return bar_chart_image, pie_chart_image

    # def _get_status_data_combined(self, records):
    #     status_data = {
    #         'open': 0,
    #         'close': 0,
    #         # 'draft': 0
    #     }
    #     for record in records:
    #         status_data[record.status] = status_data.get(record.status, 0) + 1
    #     return status_data

    def _generate_charts(self, project_name, status_data):
        # Define colors for the charts
        colors = {
            'open': 'blue',
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
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.5, project_name, ha='center')

        bar_chart_buffer = io.BytesIO()
        plt.savefig(bar_chart_buffer, format='png')
        bar_chart_buffer.seek(0)
        bar_chart_image = base64.b64encode(bar_chart_buffer.read()).decode('ascii')
        bar_chart_buffer.close()
        plt.clf()  # Clear the current figure

        # Generate Pie Chart
        fig, ax = plt.subplots(figsize=(8, 6))
        labels = list(status_data.keys())
        sizes = list(status_data.values())
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=[colors[label] for label in labels], startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

        pie_chart_buffer = io.BytesIO()
        plt.savefig(pie_chart_buffer, format='png')
        pie_chart_buffer.seek(0)
        pie_chart_image = base64.b64encode(pie_chart_buffer.read()).decode('ascii')
        pie_chart_buffer.close()
        plt.clf()  # Clear the current figure

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

    # def generate_graph_report(self):
    #     domain = self._get_domain()
    #     records = self.env['manually.set.flag'].search(domain)
    #     combined_status_data = self._get_status_data_combined(records)
    #     combined_chart_image = self._generate_combined_chart(combined_status_data)
    #     project_status_data = {}
    #     for record in records:
    #         project_name = record.project_info_id.name
    #         if project_name not in project_status_data:
    #             project_records = records.filtered(lambda r: r.project_info_id.name == project_name)
    #             project_status_data[project_name] = self._get_status_data(project_records)
    #             for project_name, status_data in project_status_data.items():
    #                 bar_chart_image, pie_chart_image = self._generate_charts(project_name, status_data)
    #                 record.pie_chart_image = pie_chart_image
    #                 record.bar_chart_image = bar_chart_image
    #                 record.combined_chart_image = bar_chart_image
    #
    #     chart_images = []
    #     for project_name, status_data in project_status_data.items():
    #         bar_chart_image, pie_chart_image = self._generate_charts(project_name, status_data)
    #         # print(pie_chart_image, 'pie_chart_image=======bar_chart_image======', bar_chart_image)
    #         chart_images.append({
    #             'project_name': project_name,
    #             'open': status_data.get('open', 0),
    #             'close': status_data.get('close', 0),
    #             'draft': status_data.get('draft', 0),
    #             'bar_chart_image': bar_chart_image,
    #             'pie_chart_image': pie_chart_image
    #         })
    #
    #     # Use the correct template and pass data
    #     return self.env.ref('custom_project_management.action_report_manually_graph_set_flag').report_action(
    #         # docids=records,
    #         docids=records[0],
    #         # data={'chart_images': chart_images}
    #     )

    def generate_graph_report(self):
        domain = self._get_domain()
        records = self.env['manually.set.flag'].search(domain)

        combined_status_data = self._get_status_data_combined(records)

        # Generate the combined chart for overall status counts
        combined_chart_image = self._generate_combined_chart(combined_status_data)

        project_status_data = {}
        for record in records:
            project_name = record.project_info_id.name
            if project_name not in project_status_data:
                project_records = records.filtered(lambda r: r.project_info_id.name == project_name)
                project_status_data[project_name] = self._get_status_data(project_records)

                for project_name, status_data in project_status_data.items():
                    bar_chart_image, pie_chart_image = self._generate_charts(project_name, status_data)
                    record.pie_chart_image = pie_chart_image
                    record.bar_chart_image = bar_chart_image
                    record.combined_chart_image = combined_chart_image

        if records:
            return self.env.ref('custom_project_management.action_report_manually_graph_set_flag').report_action(
                docids=records[0]
            )

    def generate_report(self):
        domain = self._get_domain()
        records = self.env['manually.set.flag'].search(domain)
        if records:
            return self.env.ref('custom_project_management.action_report_manually_set_flag').report_action(records)
