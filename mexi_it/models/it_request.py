# Copyright 2026 Mexilacteos (https://www.mexilacteos.com)
# License Other propietary

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItRequest(models.Model):
    _name = "it.request"
    _description = "IT Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Folio",
        required=True,
        readonly=True,
        default="New",
        copy=False,
    )
    request_type = fields.Selection(
        [
            ("asset", "Asset"),
            ("software", "Software"),
            ("support", "Support"),
        ],
        default="support",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    priority = fields.Selection(
        [("0", "Baja"), ("1", "Media"), ("2", "Alta")],
        default="1",
        required=True,
        tracking=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        default=lambda self: self._default_employee_id(),
    )
    department_id = fields.Many2one(
        related="employee_id.department_id",
        readonly=True,
    )
    job_id = fields.Many2one(
        related="employee_id.job_id",
        readonly=True,
    )
    manager_id = fields.Many2one(
        related="employee_id.parent_id",
        readonly=True,
    )

    description = fields.Text()
    date_required = fields.Date()

    asset_category = fields.Selection(
        [
            ("laptop", "Laptop"),
            ("monitor", "Monitor"),
            ("keyboard", "Keyboard"),
            ("mouse", "Mouse"),
            ("server", "Server"),
            ("other", "Other"),
        ]
    )
    asset_qty = fields.Integer(default=1)
    asset_reason = fields.Selection(
        [
            ("new_hire", "New Hire"),
            ("replacement", "Replacement"),
            ("growth", "Growth"),
            ("failure", "Failure"),
        ]
    )
    asset_spec = fields.Char()

    software_name = fields.Char()
    software_action = fields.Selection(
        [("install", "Install"), ("access", "Access")]
    )
    access_profile = fields.Selection(
        [("basic", "Basic"), ("standard", "Standard"), ("admin", "Admin")]
    )
    access_validity = fields.Selection(
        [("temporary", "Temporary"), ("permanent", "Permanent")]
    )
    business_reason = fields.Char()

    support_category = fields.Selection(
        [
            ("email", "Email"),
            ("network", "Network"),
            ("printer", "Printer"),
            ("hardware", "Hardware"),
            ("software", "Software"),
            ("other", "Other"),
        ]
    )
    support_impact = fields.Selection(
        [("blocker", "Blocker"), ("degraded", "Degraded"), ("minor", "Minor")]
    )

    approved_by_id = fields.Many2one("res.users", readonly=True)
    approved_date = fields.Datetime(readonly=True)
    reject_reason = fields.Text()
    assigned_it_user_id = fields.Many2one("res.users")
    resolution = fields.Text()
    submitted_date = fields.Datetime(readonly=True)
    done_date = fields.Datetime(readonly=True)

    equipment_employee_ids = fields.Many2many(
        "maintenance.equipment",
        compute="_compute_equipment_employee_ids",
        readonly=True,
        store=False,
    )
    equipment_department_ids = fields.Many2many(
        "maintenance.equipment",
        compute="_compute_equipment_department_ids",
        readonly=True,
        store=False,
    )

    @api.model
    def _default_employee_id(self):
        return self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )

    @api.depends("employee_id")
    def _compute_equipment_employee_ids(self):
        Equipment = self.env["maintenance.equipment"]
        for record in self:
            if record.employee_id:
                record.equipment_employee_ids = Equipment.search(
                    [("employee_id", "=", record.employee_id.id)]
                )
            else:
                record.equipment_employee_ids = Equipment.browse()

    @api.depends("employee_id")
    def _compute_equipment_department_ids(self):
        Equipment = self.env["maintenance.equipment"]
        for record in self:
            if record.employee_id.department_id:
                record.equipment_department_ids = Equipment.search(
                    [("department_id", "=", record.employee_id.department_id.id)]
                )
            else:
                record.equipment_department_ids = Equipment.browse()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "it.request"
                ) or "New"
        return super().create(vals_list)

    def write(self, vals):
        blocked_fields = {
            "request_type",
            "description",
            "employee_id",
            "asset_category",
            "asset_qty",
            "asset_reason",
            "asset_spec",
            "software_name",
            "software_action",
            "access_profile",
            "access_validity",
            "business_reason",
            "support_category",
            "support_impact",
        }
        if blocked_fields.intersection(vals) and any(
            record.state != "draft" for record in self
        ):
            raise UserError(
                _("You can only change request details in draft state.")
            )
        return super().write(vals)

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            if not record.description:
                raise UserError(_("Description is required to submit."))
            record._validate_request_type()
            record.write(
                {
                    "state": "submitted",
                    "submitted_date": fields.Datetime.now(),
                }
            )
            record.message_post(body=_("Request submitted."))

    def action_approve(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be approved."))
            if record.request_type not in ("asset", "software"):
                raise UserError(
                    _("Only asset or software requests can be approved.")
                )
            record.write(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_date": fields.Datetime.now(),
                }
            )
            record.message_post(body=_("Request approved."))

    def action_reject(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be rejected."))
            if record.request_type not in ("asset", "software"):
                raise UserError(
                    _("Only asset or software requests can be rejected.")
                )
            if not record.reject_reason:
                raise UserError(_("Reject reason is required."))
            record.write({"state": "rejected"})
            record.message_post(
                body=_("Request rejected. Reason: %s") % record.reject_reason
            )

    def action_start(self):
        for record in self:
            if record.request_type == "support":
                if record.state != "submitted":
                    raise UserError(
                        _("Support requests must be submitted to start.")
                    )
            else:
                if record.state != "approved":
                    raise UserError(
                        _("Asset/software requests must be approved to start.")
                    )
            values = {"state": "in_progress"}
            if not record.assigned_it_user_id:
                values["assigned_it_user_id"] = self.env.user.id
            record.write(values)
            record.message_post(body=_("Work started."))

    def action_done(self):
        for record in self:
            if record.state != "in_progress":
                raise UserError(_("Only in-progress requests can be done."))
            if not record.resolution:
                raise UserError(_("Resolution is required to finish."))
            record.write(
                {"state": "done", "done_date": fields.Datetime.now()}
            )
            record.message_post(
                body=_("Request completed. Resolution: %s") % record.resolution
            )

    def _validate_request_type(self):
        self.ensure_one()
        if self.request_type == "asset":
            if not self.asset_category:
                raise UserError(_("Asset category is required."))
            if not self.asset_reason:
                raise UserError(_("Asset reason is required."))
            if self.asset_qty <= 0:
                raise UserError(_("Asset quantity must be greater than zero."))
        elif self.request_type == "software":
            missing = []
            if not self.software_name:
                missing.append(_("Software name"))
            if not self.software_action:
                missing.append(_("Software action"))
            if not self.access_profile:
                missing.append(_("Access profile"))
            if not self.access_validity:
                missing.append(_("Access validity"))
            if not self.business_reason:
                missing.append(_("Business reason"))
            if missing:
                raise UserError(
                    _("Missing required fields: %s") % ", ".join(missing)
                )
        elif self.request_type == "support":
            if not self.support_category:
                raise UserError(_("Support category is required."))
            if not self.support_impact:
                raise UserError(_("Support impact is required."))
