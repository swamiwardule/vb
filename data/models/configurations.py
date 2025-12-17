from odoo import models, fields, api, _
from datetime import datetime, timedelta
from itertools import filterfalse
import logging
_logger = logging.getLogger(__name__)


class FrameWorkBusinessUnit(models.Model):
    _name = 'framework.businessunit'
    #_rec_name = 'name'

    # name = fields.Char('Name')
    # project_id = fields.Many2one('project.info','Project')

class ConstructionWorkOrder(models.Model):
    _name = 'construction.workorder'

class ConstructionWorkOrderAmendment(models.Model):
    _name = 'construction.workorderamendment'

class ConstructionWorkDone(models.Model):
    _name = 'construction.workdone'

class FinanceLedger(models.Model):
    _name = 'financ.eledger'

class AmendmentType(models.Model):
    _name = 'amendment.type'
    
    
