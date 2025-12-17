from odoo import models, fields, api, _


class WorkDoneActivities(models.Model):
    _name = "work.done.activity"
    _description = "Work done activities"

    TenantId = fields.Char(string="TenantId")
    FiscalYearId = fields.Char(string="FiscalYearId")
    BUId = fields.Char(string="BUId")
    EntryTypeId = fields.Char(string="EntryTypeId")
    DocumentNo = fields.Char(string="DocumentNo")
    DocumentDate = fields.Char(string="DocumentDate")
    DocumentDateUTC = fields.Char(string="DocumentDateUTC")
    ProvisionalDocNo = fields.Char(string="ProvisionalDocNo")
    ProvisionalDocType = fields.Char(string="ProvisionalDocType")
    PrefixType = fields.Char(string="PrefixType")
    WorkOrderId = fields.Char(string="WorkOrderId")
    PartyLedger = fields.Char(string="PartyLedger")
    PartyMainLedger = fields.Char(string="PartyMainLedger")
    IsOpenWorkDone = fields.Char(string="IsOpenWorkDone")
    EntrySerialNo = fields.Char(string="EntrySerialNo")
    BillOrItemWiseBillingTerm = fields.Char(string="BillOrItemWiseBillingTerm")
    POSStateId = fields.Char(string="POSStateId")
    POSGSTStateId = fields.Char(string="POSGSTStateId")
    PaymentTermGroupId = fields.Char(string="PaymentTermGroupId")
    CategoryId = fields.Char(string="CategoryId")
    GSTINId = fields.Char(string="GSTINId")
    Amount = fields.Char(string="Amount")
    IsImported = fields.Char(string="IsImported")
    WorkflowId = fields.Char(string="WorkflowId")
    ApprovalLevel = fields.Char(string="ApprovalLevel")
    ApproverId = fields.Char(string="ApproverId")
    StatusUpdatedOn = fields.Char(string="StatusUpdatedOn")
    ApprovalStatus = fields.Char(string="ApprovalStatus")
    UIID = fields.Char(string="UIID")
    Attachments = fields.Char(string="Attachments")
    SubProjectId = fields.Char(string="SubProjectId")
    BudgetId = fields.Char(string="BudgetId")
    GrossAmount = fields.Char(string="GrossAmount")
    NetAmount = fields.Char(string="NetAmount")
    EquipmentItemId = fields.Char(string="EquipmentItemId")
    RegistrationNo = fields.Char(string="RegistrationNo")
    WorkDoneRemark = fields.Char(string="WorkDoneRemark")


class WorkOrderActivity(models.Model):
    _name = "work.order.activity"
    _description = "Work order activity"

    TenantId = fields.Char(string="TenantId")
    WorkOrderId = fields.Char(string="WorkOrderId")
    AmendmentType = fields.Char(string="AmendmentType")
    RefId = fields.Char(string="RefId")


