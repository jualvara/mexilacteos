# Copyright 2026 Mexilacteos (https://www.mexilacteos.com)
# License OPL-1.0

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItRequest(models.Model):
    """IT Request Management System.

    Handles three types of requests:
    - Asset: Hardware/equipment requests with approval flow
    - Software: Software installation/access with approval flow
    - Support: Technical support requests (direct to IT)
    """

    _name = "it.request"
    _description = "IT Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------
    name = fields.Char(
        string="Folio",
        required=True,
        readonly=True,
        default="New",
        copy=False,
    )
    request_type = fields.Selection(
        selection=[
            ("asset", "Asset"),
            ("software", "Software"),
            ("support", "Support"),
        ],
        default="support",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
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
        selection=[("0", "Low"), ("1", "Medium"), ("2", "High")],
        default="1",
        required=True,
        tracking=True,
    )

    # Employee information
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
        default=lambda self: self._default_employee_id(),
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        related="employee_id.department_id",
        readonly=True,
        store=False,
    )
    job_id = fields.Many2one(
        comodel_name="hr.job",
        string="Job Position",
        related="employee_id.job_id",
        readonly=True,
        store=False,
    )
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Manager",
        related="employee_id.parent_id",
        readonly=True,
        store=False,
    )

    # Request details
    description = fields.Text(string="Description")
    date_required = fields.Date(
        string="Required By",
        default=lambda self: fields.Date.today()
        + __import__("datetime").timedelta(days=7),
    )

    # Asset request fields
    asset_category = fields.Selection(
        selection=[
            ("laptop", "Laptop"),
            ("monitor", "Monitor"),
            ("keyboard", "Keyboard"),
            ("mouse", "Mouse"),
            ("server", "Server"),
            ("other", "Other"),
        ],
        string="Asset Category",
    )
    asset_qty = fields.Integer(string="Quantity", default=1)
    asset_reason = fields.Selection(
        selection=[
            ("new_hire", "New Hire"),
            ("replacement", "Replacement"),
            ("growth", "Growth"),
            ("failure", "Failure"),
        ],
        string="Reason",
    )
    asset_spec = fields.Char(string="Technical Specifications")

    # Software request fields
    software_name = fields.Char(string="Software Name")
    software_action = fields.Selection(
        selection=[("install", "Install"), ("access", "Access")],
        string="Action Required",
    )
    access_profile = fields.Selection(
        selection=[
            ("basic", "Basic"),
            ("standard", "Standard"),
            ("admin", "Admin"),
        ],
        string="Access Profile",
    )
    access_validity = fields.Selection(
        selection=[("temporary", "Temporary"), ("permanent", "Permanent")],
        string="Access Validity",
    )
    business_reason = fields.Char(string="Business Justification")

    # Support request fields
    support_category = fields.Selection(
        selection=[
            ("email", "Email"),
            ("network", "Network"),
            ("printer", "Printer"),
            ("hardware", "Hardware"),
            ("software", "Software"),
            ("other", "Other"),
        ],
        string="Support Category",
    )
    support_impact = fields.Selection(
        selection=[
            ("blocker", "Blocker"),
            ("degraded", "Degraded"),
            ("minor", "Minor"),
        ],
        string="Business Impact",
    )

    # Approval and assignment
    approved_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Approved By",
        readonly=True,
    )
    approved_date = fields.Datetime(string="Approval Date", readonly=True)
    reject_reason = fields.Text(string="Rejection Reason")
    assigned_it_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned IT User",
    )
    resolution = fields.Text(string="Resolution")

    # Timeline tracking
    submitted_date = fields.Datetime(string="Submitted Date", readonly=True)
    done_date = fields.Datetime(string="Completion Date", readonly=True)

    # Equipment reference (computed)
    equipment_employee_ids = fields.Many2many(
        comodel_name="maintenance.equipment",
        compute="_compute_equipment_employee_ids",
        string="Employee Equipment",
        readonly=True,
        store=False,
    )
    equipment_department_ids = fields.Many2many(
        comodel_name="maintenance.equipment",
        compute="_compute_equipment_department_ids",
        string="Department Equipment",
        readonly=True,
        store=False,
    )

    # Metrics for visual indicators
    days_since_creation = fields.Integer(
        compute="_compute_days_metrics",
        string="Days Since Creation",
    )
    days_in_current_state = fields.Integer(
        compute="_compute_days_metrics",
        string="Days in Current State",
    )
    color = fields.Integer(
        compute="_compute_color",
        string="Color Index",
    )

    # -------------------------------------------------------------------------
    # Defaults
    # -------------------------------------------------------------------------
    @api.model
    def _default_employee_id(self):
        """Get employee record for current user."""
        return self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------
    @api.depends("employee_id")
    def _compute_equipment_employee_ids(self):
        """Fetch equipment assigned to request employee."""
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
        """Fetch equipment assigned to employee's department."""
        Equipment = self.env["maintenance.equipment"]
        for record in self:
            if record.employee_id.department_id:
                record.equipment_department_ids = Equipment.search(
                    [("department_id", "=", record.employee_id.department_id.id)]
                )
            else:
                record.equipment_department_ids = Equipment.browse()

    @api.depends("create_date", "submitted_date", "approved_date", "state")
    def _compute_days_metrics(self):
        """Calculate days since creation and in current state."""
        for record in self:
            now = fields.Datetime.now()
            if record.create_date:
                delta = now - record.create_date
                record.days_since_creation = delta.days
            else:
                record.days_since_creation = 0

            state_date_map = {
                "submitted": record.submitted_date,
                "approved": record.approved_date,
                "in_progress": record.approved_date or record.submitted_date,
                "done": record.done_date,
            }
            state_date = state_date_map.get(record.state)
            if state_date:
                delta = now - state_date
                record.days_in_current_state = delta.days
            else:
                record.days_in_current_state = 0

    @api.depends("priority", "state", "days_since_creation")
    def _compute_color(self):
        """Compute kanban color based on priority and age."""
        for record in self:
            if record.state in ["done", "rejected"]:
                record.color = 10
            elif record.priority == "2":
                record.color = 1
            elif record.priority == "1":
                record.color = 3
            elif record.days_since_creation > 7:
                record.color = 7
            else:
                record.color = 10

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence and subscribe default followers."""
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("it.request") or "New"
                )
        records = super().create(vals_list)
        records._ensure_default_followers()
        return records

    def write(self, vals):
        """Block request field changes after draft state."""
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
            raise UserError(_("Request details can only be modified in draft state."))
        result = super().write(vals)
        if "assigned_it_user_id" in vals:
            self._ensure_default_followers()
        return result

    # -------------------------------------------------------------------------
    # State Transition Actions
    # -------------------------------------------------------------------------
    def action_submit(self):
        """Submit request for approval or direct IT assignment."""
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
            record._notify_status_change(_("→ Submitted by %s") % record.employee_id.name)

            if record.request_type in ("asset", "software") and record.manager_id.user_id:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=record.manager_id.user_id.id,
                    note=_("Please review and approve request %s") % record.name,
                )
            elif record.request_type == "support":
                it_group = self.env.ref(
                    "mexi_it.group_it_request_it", raise_if_not_found=False
                )
                if it_group and it_group.users:
                    # Auto-assign first IT user if not assigned
                    if not record.assigned_it_user_id:
                        record.assigned_it_user_id = it_group.users[0]
                    # Create activity for all IT group members
                    for it_user in it_group.users:
                        record.activity_schedule(
                            "mail.mail_activity_data_todo",
                            user_id=it_user.id,
                            note=_("Support request %s needs attention") % record.name,
                        )

    def action_approve(self):
        """Approve request and assign IT activity."""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be approved."))
            if record.request_type not in ("asset", "software"):
                raise UserError(_("Only asset or software requests can be approved."))
            record.write(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_date": fields.Datetime.now(),
                }
            )
            if self.env.user.partner_id:
                record.message_subscribe(partner_ids=[self.env.user.partner_id.id])
            record._notify_status_change(_("→ Approved by %s") % self.env.user.name)

            if record.assigned_it_user_id:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=record.assigned_it_user_id.id,
                    note=_("Work on approved request %s") % record.name,
                )
            else:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=self.env.user.id,
                    note=_("Assign an IT technician to request %s") % record.name,
                )

    def action_reject(self):
        """Reject request with reason."""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be rejected."))
            if record.request_type not in ("asset", "software"):
                raise UserError(_("Only asset or software requests can be rejected."))
            if not record.reject_reason:
                raise UserError(_("Reject reason is required."))
            record.write({"state": "rejected"})
            record._notify_status_change(
                _("→ Rejected by %s. Reason: %s")
                % (self.env.user.name, record.reject_reason)
            )

    def action_start(self):
        """Start work on request."""
        for record in self:
            if record.request_type == "support":
                if record.state != "submitted":
                    raise UserError(_("Support requests must be submitted to start."))
            else:
                if record.state != "approved":
                    raise UserError(
                        _("Asset/software requests must be approved to start.")
                    )
            if not record.assigned_it_user_id:
                raise UserError(_("Please assign an IT user before starting work."))
            record.write({"state": "in_progress"})
            record._notify_status_change(
                _("→ Work started by %s") % record.assigned_it_user_id.name
            )

    def action_done(self):
        """Complete request with resolution."""
        for record in self:
            if record.state != "in_progress":
                raise UserError(_("Only in-progress requests can be done."))
            if not record.resolution:
                raise UserError(_("Resolution is required to finish."))
            record.write({"state": "done", "done_date": fields.Datetime.now()})
            record._notify_status_change(
                _("→ Completed by %s. Resolution: %s")
                % (self.env.user.name, record.resolution)
            )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    def _validate_request_type(self):
        """Validate type-specific required fields before submission."""
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
                raise UserError(_("Missing required fields: %s") % ", ".join(missing))
        elif self.request_type == "support":
            if not self.support_category:
                raise UserError(_("Support category is required."))
            if not self.support_impact:
                raise UserError(_("Support impact is required."))

    # -------------------------------------------------------------------------
    # Smart Button Actions
    # -------------------------------------------------------------------------
    def action_view_equipment(self):
        """Open employee equipment list."""
        self.ensure_one()
        return {
            "name": _("Employee Equipment"),
            "type": "ir.actions.act_window",
            "res_model": "maintenance.equipment",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.employee_id.id)],
            "context": {"default_employee_id": self.employee_id.id},
        }

    def action_view_department_equipment(self):
        """Open department equipment list."""
        self.ensure_one()
        return {
            "name": _("Department Equipment"),
            "type": "ir.actions.act_window",
            "res_model": "maintenance.equipment",
            "view_mode": "list,form",
            "domain": [("department_id", "=", self.employee_id.department_id.id)],
            "context": {"default_department_id": self.employee_id.department_id.id},
        }

    # -------------------------------------------------------------------------
    # Notification System
    # -------------------------------------------------------------------------
    def _collect_notification_partners(self):
        """Collect all partners to notify: employee, manager, approver, IT."""
        partners = self.env["res.partner"]
        for record in self:
            if record.employee_id.user_id.partner_id:
                partners |= record.employee_id.user_id.partner_id
            if record.manager_id.user_id.partner_id:
                partners |= record.manager_id.user_id.partner_id
            if record.approved_by_id.partner_id:
                partners |= record.approved_by_id.partner_id
            if record.assigned_it_user_id.partner_id:
                partners |= record.assigned_it_user_id.partner_id
        return partners

    def _ensure_default_followers(self):
        """Subscribe relevant partners to chatter notifications."""
        partners = self._collect_notification_partners()
        if partners:
            self.message_subscribe(partner_ids=partners.ids)

    def _notify_status_change(self, body):
        """Post chatter message and notify followers."""
        partners = self._collect_notification_partners()
        self.message_post(
            body=body,
            partner_ids=partners.ids,
            subtype_xmlid="mail.mt_comment",
        )
