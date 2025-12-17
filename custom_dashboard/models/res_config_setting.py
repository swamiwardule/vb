
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    on_off_value = fields.Boolean(string="Fields Functon On/Off", default=True)

    @api.model
    def set_values(self):
        """ Save the boolean value in system parameters """
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('custom_project_management.on_off_value', self.on_off_value)
        return res

    @api.model
    def get_values(self):
        """ Get the stored value from system parameters """
        res = super(ResConfigSettings, self).get_values()
        res.update(
            on_off_value=self.env['ir.config_parameter'].sudo().get_param('custom_project_management.on_off_value', default=False),
        )
        return res
