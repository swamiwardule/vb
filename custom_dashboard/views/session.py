import datetime

import requests

from odoo import fields
from odoo.http import request, root
from odoo.service import security
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component
from werkzeug.exceptions import BadRequest
from datetime import datetime, timedelta
import math
import random
import logging
from odoo.http import request, route, Response
import json
from collections import Counter
from pytz import timezone
from odoo import http
import base64
_logger = logging.getLogger(__name__)


def _rotate_session(httprequest):
    if httprequest.session.rotate:
        root.session_store.delete(httprequest.session)
        httprequest.session.sid = root.session_store.generate_key()
        if httprequest.session.uid:
            httprequest.session.session_token = security.compute_session_token(
                httprequest.session, request.env
            )
        httprequest.session.modified = True


class SessionAuthenticationService(Component):
    _inherit = "base.rest.service"
    _name = "session.authenticate.service"
    _usage = "auth"
    _collection = "session.rest.services"

    @restapi.method([(["/login"], "POST")], auth="public")
    def authenticate(self):
        params = request.params
        db_name = params.get("db")
        request.session.authenticate(
            db_name, params["login"], params["password"])
        result = request.env["ir.http"].session_info()
        # avoid to rotate the session outside of the scope of this method
        # to ensure that the session ID does not change after this method
        _rotate_session(request)
        request.session.rotate = False
        expiration = datetime.utcnow() + timedelta(days=90)
        result["session"] = {
            "sid": request.session.sid,
            "expires_at": fields.Datetime.to_string(expiration),
        }
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        base_url = base_url + \
            "/web/image?model=res.users&field=image_1920&id=" + \
            str(result['uid'])
        result['profile_image'] = base_url
        approver_group_id = self.env.ref(
            'custom_project_management.group_quality_approver')
        approver_group_id = self.env['res.groups'].sudo().browse(
            approver_group_id.id)
        checker_group_id = self.env.ref(
            'custom_project_management.group_quality_checker')
        checker_group_id = self.env['res.groups'].sudo().browse(
            checker_group_id.id)

        maker_group_id = self.env.ref(
            'custom_project_management.group_quality_maker')
        maker_group_id = self.env['res.groups'].sudo().browse(
            maker_group_id.id)

        del_activity_group_id = self.env.ref(
            'custom_project_management.group_delete_activity')
        del_activity_group_id = self.env['res.groups'].sudo().browse(
            del_activity_group_id.id)
        result['del_activity_users'] = False
        if result['uid'] in del_activity_group_id.users.ids:
            result['del_activity_users'] = True

        if result['uid'] in approver_group_id.users.ids:
            result['user_type'] = 'approver'
        elif result['uid'] in checker_group_id.users.ids:
            result['user_type'] = 'checker'
        elif result['uid'] in maker_group_id.users.ids:
            result['user_type'] = 'maker'

        else:
            result['user_type'] = 'employee'

        return result

    @restapi.method([(["/signup"], "POST")], auth="public")
    def signup(self):
        params = request.params
        user_id = self.env['res.users'].sudo().search(
            [('login', '=', params["email"])], limit=1)
        if user_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'User already exists', }),
                            content_type='application/json;charset=utf-8', status=200)
        db_name = params.get("db")
        data = {
            'name': params["name"],
            'login': params["email"],
            'password': params["password"]
        }
        if params.get('lat'):
            data.update({
                'lat': params.get('lat')
            })
        if params.get('long'):
            data.update({
                'longi': params.get('long')
            })

        user_id = self.env["res.users"].sudo().create(data)
        user_id.sudo()._change_password(params["password"])
        if params.get('maker'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_maker')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        if params.get('checker'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_checker')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        if params.get('approver'):
            group_id = self.env.ref(
                'custom_project_management.group_quality_approver')
            if group_id:
                group_id.sudo().write({
                    'users': [(4, user_id.id)]
                })
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'User Signup Done', }),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/signout"], "POST")], auth="user")
    def get_partner(self):
        partner_id = self.env['res.partner'].sudo().search([])

        return {
            'partner_id': str(partner_id.ids)
        }

    @restapi.method([(["/logout"], "POST")], auth="user")
    def logout(self):
        request.session.logout(keep_db=True)
        return {"message": "Successful logout"}

    @restapi.method([(["/get/assigned/projects"], "POST")], auth="user")
    def get_assigned_projects(self):

        project_ids = self.env['project.info'].sudo().search(
            [('assigned_to_ids', 'in', self.env.user.id)])
        data_dict = []
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        for project in project_ids:
            url = base_url+"/web/image?model=project.info&field=image&id=" + \
                str(project.id)
            # print ("--base_url----",base_url)
            data_dict.append({
                'name': project.name,
                'image': url,
                'project_id': project.id,
                'progress': project.project_progress_bar or 0.0,
            })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data_dict}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/nc"], "POST")], auth="user")
    def get_project_nc(self):

        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        project_data = self.env['project.info'].sudo(
        ).get_project_nc_data(params.get('project_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/tower_floor/nc"], "POST")], auth="user")
    def get_project_tower_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_nc_data(
            params.get('project_id'), params.get('tower_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/floor/nc"], "POST")], auth="user")
    def get_project_tower_floor_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('floor_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_floor_nc_data(
            params.get('project_id'), params.get('tower_id'), params.get('floor_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activity/nc"], "POST")], auth="user")
    def get_floor_activity_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('floor_id') and not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project, Tower, Floor, Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_floor_activity_nc(params.get(
            'project_id'), params.get('tower_id'), params.get('floor_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activity_type/nc"], "POST")], auth="user")
    def get_floor_activity_type_nc(self):

        params = request.params

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity, Type ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_floor_activity_type_nc(
            params.get('activity_id'), params.get('type_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/checklist/nc"], "POST")], auth="user")
    def get_floor_checklist_nc(self):

        params = request.params
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo(
        ).get_floor_checklist_nc(params.get('checklist_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # For Flat Start

    @restapi.method([(["/get/project/tower_flat/nc"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_towerflat_nc_data(
            params.get('project_id'), params.get('tower_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/flat/nc"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('flat_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID, Tower Id and Value'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_project_tower_flat_nc_data(
            params.get('project_id'), params.get('tower_id'), params.get('flat_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Tower Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activity/nc"], "POST")], auth="user")
    def get_flat_activity_nc(self):
        _logger.info("--get_flat_activity_nc----")

        params = request.params
        if not params.get('project_id') and not params.get('tower_id') and not params.get('flat_id') and not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project, Tower, Floor, Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_flat_activity_nc(params.get(
            'project_id'), params.get('tower_id'), params.get('flat_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activity_type/nc"], "POST")], auth="user")
    def get_flat_activity_type_nc(self):

        params = request.params
        if not params.get('activity_id') and not params.get('type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity and Type Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo().get_flat_activity_type_nc(
            params.get('type_id'), params.get('activity_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/checklist/nc"], "POST")], auth="user")
    def get_flat_checklist_nc(self):
        params = request.params
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        project_data = self.env['project.info'].sudo(
        ).get_flat_checklist_nc(params.get('checklist_id'))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activty Nc Fetch', 'project_data': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # For  Flats End

    @restapi.method([(["/get/project_info"], "POST")], auth="user")
    def get_project_info(self):

        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        project_id = self.env['project.info'].sudo().browse(
            int(params.get('project_id')))
        if not project_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        project_image_url = base_url + \
            "/web/image?model=project.info&field=image&id="+str(project_id.id)
        data = {
            'project_name': project_id.name,
            'image_url': project_image_url,
        }

        list_data = []
        for project_info in project_id.project_details_line:
            line_url = base_url+"/web/image?model=project.details&field=image&id=" + \
                str(project_info.id)
            list_data.append({
                'name': project_info.name,
                'image': line_url,
                'checklist_id': project_info.id,
            })
        data['checklist_data'] = list_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/checklist/tower"], "POST")], auth="user")
    def get_checklist_tower(self):
        params = request.params
        user_id = False
        list_data = []
        progress = 0.0
        if params.get('user_id'):
            user_id = params.get('user_id')
        if not params.get('checklist_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        checklist_id = self.env['project.details'].sudo().browse(
            int(params.get('checklist_id')))
        if not checklist_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Checklist ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        checklist_image_url = base_url + \
            "/web/image?model=project.details&field=image&id=" + \
            str(checklist_id.id)

        data = {
            'checklist_name': checklist_id.name,
            'image_url': checklist_image_url,
            'checklist_id': checklist_id.id,
            # 'progress':checklist_id.project_id.project_progress_bar or 0.0,
        }

        for tower in checklist_id.tower_id:
            progress = tower.project_id.project_progress_bar or 0.0
            # _logger.info("---------6666------")
            user_ids = list(tower.assigned_to_ids.ids)
            if int(user_id) in user_ids:
                list_data.append({
                    'name': tower.name,
                    'tower_id': tower.id,
                    'progress': tower.tower_progress_percentage,  # prject overall progress

                })
        data.update({'progress': progress})
        data['tower_data'] = list_data
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/checklist/count"], "POST")], auth="user")
    def get_tower_checklist_count(self):
        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        tower_id = self.env['project.tower'].sudo().browse(
            int(params.get('tower_id')))
        if not tower_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        data = {
            'tower_name': tower_id.name,
            'tower_id': tower_id.id
        }
        floor_data = []
        for floor in tower_id.tower_floor_line_id:
            submit_count = checked_count = approve_count = 0

            for activity in floor.activity_ids:

                status_counts = Counter(
                    act_type.status for act_type in activity.activity_type_ids)
                submit_count = status_counts.get('submit', 0)
                checked_count = status_counts.get('checked', 0)
                approve_count = status_counts.get('approve', 0)

                # for act_type in activity.activity_type_ids:
                #     status = act_type.status
                #     if status == 'submit':
                #         submit_count += 1
                #     if status == 'checked':
                #         checked_count += 1
                #     if status == 'approve':
                #         approve_count += 1

            floor_data.append({
                'name': floor.name,
                'floor_id': floor.id,
                'maker_count': submit_count,
                'checker_count': checked_count,
                'approver_count': approve_count,

            })
        data['floor_data'] = floor_data
        flat_data = []
        for flat in tower_id.tower_flat_line_id:
            submit_count = checked_count = approve_count = 0
            for activity in flat.activity_ids:

                status_counts = Counter(
                    act_type.status for act_type in activity.activity_type_ids)
                submit_count = status_counts.get('submit', 0)
                checked_count = status_counts.get('checked', 0)
                approve_count = status_counts.get('approve', 0)

            flat_data.append({
                'name': flat.name,
                # this should be flat_id
                'floor_id': flat.id,
                'maker_count': submit_count,
                'checker_count': checked_count,
                'approver_count': approve_count,
            })

        data['flat_data'] = flat_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower info Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/floor"], "POST")], auth="user")
    def get_flat_floor_by_tower_test(self):
        params = request.params
        if not params.get('tower_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        tower_id = self.env['project.tower'].sudo().browse(
            int(params.get('tower_id')))
        if not tower_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Tower ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        data = {
            "tower_name": tower_id.name,
            "tower_id": tower_id.id,
            "progress": tower_id.tower_progress_percentage,  # tower progress
        }

        flat_maker = flat_checker = flat_approver = flat_checklist = 0
        floor_maker = floor_checker = floor_approver = floor_checklist = 0

        floor_data = []
        for floor in tower_id.tower_floor_line_id:
            submit_count = checked_count = approve_count = total_checklist_count = 0

            for activity in floor.activity_ids:
                for act_type in activity.activity_type_ids:
                    status = act_type.status
                    total_checklist_count += 1
                    if status == 'submit':
                        submit_count += 1
                    if status == 'checked':
                        checked_count += 1
                    if status == 'approve':
                        approve_count += 1

            floor_maker += submit_count+checked_count+approve_count
            floor_checker += checked_count+approve_count
            floor_approver += approve_count
            floor_checklist += total_checklist_count

            floor_data.append({
                "name": floor.name,
                "floor_id": floor.id,
                "progress": floor.floor_progress_percentage or 0.0,
                "total_count": total_checklist_count,
                # "maker_count": submit_count,
                # "checker_count": checked_count,
                # "approver_count": approve_count,
                "maker_count": submit_count+checked_count+approve_count,
                "checker_count": checked_count+approve_count,
                "approver_count": approve_count,
            })

        floor_total = floor_checklist
        flat_data = []
        for flat in tower_id.tower_flat_line_id:
            submit_count = checked_count = approve_count = total_checklist_count = 0
            for activity in flat.activity_ids:
                for act_type in activity.activity_type_ids:
                    status = act_type.status
                    total_checklist_count += 1
                    if status == 'submit':
                        submit_count += 1
                    if status == 'checked':
                        checked_count += 1
                    if status == 'approve':
                        approve_count += 1

            flat_maker += submit_count+checked_count+approve_count
            flat_checker += checked_count+approve_count
            flat_approver += approve_count
            flat_checklist += total_checklist_count

            flat_data.append({
                "name": flat.name,
                "flat_id": flat.id,
                "progress": flat.flats_progress_percentage or 0.0,
                "total_count": total_checklist_count,
                # "maker_count": submit_count,
                # "checker_count": checked_count,
                # "approver_count": approve_count,
                "maker_count": submit_count+checked_count+approve_count,
                "checker_count": checked_count+approve_count,
                "approver_count": approve_count,
            })

        flat_total = flat_checklist
        data["tower_total_count"] = flat_total+floor_total
        data["tower_maker_count"] = flat_maker+floor_maker
        data["tower_checker_count"] = flat_checker+floor_checker
        data["tower_approver_count"] = flat_approver+floor_approver
        data["flat_total_count"] = flat_total
        data["flat_maker_count"] = flat_maker
        data["flat_checker_count"] = flat_checker
        data["flat_approver_count"] = flat_approver
        data["floor_total_count"] = floor_total
        data["floor_maker_count"] = floor_maker
        data["floor_checker_count"] = floor_checker
        data["floor_approver_count"] = floor_approver
        data['list_flat_data'] = flat_data
        data['list_floor_data'] = floor_data

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower info Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flat/activites"], "POST")], auth="user")
    def get_flat_activites(self):
        params = request.params
        if not params.get('flat_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        flat_id = self.env['project.flats'].sudo().browse(
            int(params.get('flat_id')))
        if not flat_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = {
            'flat_name': flat_id.name,
            'flat_id': flat_id.id
        }

        list_flat_data = []
        total_count = 0
        for activity in flat_id.activity_ids:

            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                if status == 'checked':
                    checked += 1
                if status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            if approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            list_flat_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': str(activity.write_date),
                'activity_type_status': activity_type_status,
                'progress': activity.progress_percentage or 0.0,
                'color': color,
            })
        data['list_flat_data'] = list_flat_data
        data['total_count'] = total_count

        # _logger.info("-----data------,%s",data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floor/activites"], "POST")], auth="user")
    def get_floor_activites(self):
        params = request.params
        if not params.get('floor_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Flat ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        floor_id = self.env['project.floors'].sudo().browse(
            int(params.get('floor_id')))
        if not floor_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Floor ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = {
            'floor_name': floor_id.name,
            'floor_id': floor_id.id
        }
        list_floor_data = []
        total_count = 0
        for activity in floor_id.activity_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            activity_type_status = False

            for act_type in activity.activity_type_ids:
                status = act_type.status
                count += 1
                if status == 'draft':
                    draft += 1
                if status == 'checked':
                    checked += 1
                if status == 'approve':
                    approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            if approve and not draft and not checked:
                color = 'green'
                activity_type_status = True

            list_floor_data.append({
                'name': activity.name,
                'desc': '',
                'activity_id': activity.id,
                'write_date': str(activity.write_date),
                'activity_type_status': activity_type_status,
                'progress': activity.progress_percentage or 0.0,
                'color': color,
            })
        data['list_floor_data'] = list_floor_data
        data['total_count'] = total_count

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity info Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    # color coding

    @restapi.method([(["/get/checklist"], "POST")], auth="user")
    def get_checklist_by_activity(self):
        params = request.params
        user_id = ''
        role = ''

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_id = self.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        if not activity_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        _logger.info(
            "-------------------activity_id:-----------------", activity_id)
        data = {
            'activity_name': activity_id.name,
            'activity_id': activity_id.id,
            'activity_progress': activity_id.progress_percentage,
            'project_id': activity_id.project_id.id,
            'project_name': activity_id.project_id.name,
            'tower_id': activity_id.tower_id.id,
            'tower_name': activity_id.tower_id.name,
            'floor_id': activity_id.floor_id.id,
            'floor_name': activity_id.floor_id.name,
        }

        # _logger.info("------------------data----------------------", data)

        list_checklist_data = []
        list_checklist_line = []

        # pre,during,post
        total_count = 0

        for activity in activity_id.activity_type_ids:
            count = draft = checked = approve = 0
            color = 'yellow'
            reject = ''
            if activity.type_status:
                if activity.type_status == 'checker_reject' or activity.type_status == 'approver_reject':
                    reject = activity.type_status

            status = activity.status
            count += 1
            if status == 'draft':
                draft += 1
            if status == 'checked':
                checked += 1
            if status == 'approve':
                approve += 1

            total_count += count
            if draft and not checked and not approve:
                color = 'red'
            if approve and not draft and not checked:
                color = 'green'

            line_data = []
            # logs = self.env['project.checklist.line.log'].search([('activity_type_id','=',activity.id)])
            for checklist_line in activity.checklist_ids:
                history = []
                log_lines = self.env['project.checklist.line.log'].search(
                    [('line_id', '=', checklist_line.id)])

                for line in log_lines:
                    image_link = []
                    for url in line.checklist_line_log_line:
                        # _logger.info("-url------,%s",str(url))
                        image_link.append(url.url)
                    history.append({
                        'id': line.id,
                        'name': line.checklist_template_id.name,
                        'reason': line.reason,
                        'is_pass': line.is_pass,
                        'name': line.checklist_template_id.name,
                        'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                        'update_time': str(line.datetime),
                        'image_url': image_link,
                        'submitted': 'false',
                    })

                image_link = []
                for image_line in checklist_line.image_ids:
                    checklist_image_url = str(
                        base_url)+"/web/image?model=project.checklist.line.images&field=image&id="+str(image_line.id)
                    image_link.append(checklist_image_url)

                line_data.append({
                    'name': checklist_line.checklist_template_id.name,
                    'reason': checklist_line.reason,
                    'is_pass': checklist_line.is_pass,
                    'name': checklist_line.checklist_template_id.name,
                    'image_url': image_link,
                    'line_id': checklist_line.id,
                    'history': history
                    # 'submittedBy':{'id':user_id,'name':user_record.name,'role':role},
                    # 'update_time':datetime.datetime.now(),
                })

            activity_status = activity.status
            if activity.status == 'approver_reject':
                activity_status = 'submit'
            if activity.status == 'checker_reject':
                activity_status = 'draft'

            try:
                image_urls = []
                if activity.activity_type_img_ids:
                    for img in activity.activity_type_img_ids:
                        if img.img_type == 'pat':
                            checklist_image_url = str(
                                base_url)+"/web/image?model=project.activity.type.image&field=overall_img&id="+str(img.id)
                            image_urls.append(str(checklist_image_url))
            except Exception as e:
                _logger.info(
                    "-get_project_activity_details--exception- overall_images-----,%s", str(e))
                pass
            # _logger.info("-------color-----,%s",str(color))

            list_checklist_data.append({
                'name': activity.name,
                'activity_type_id': activity.id,
                'activity_status': activity_status,
                'activity_type_progress': activity.progress_percentage,
                'project_id': activity.project_id.id,
                'project_name': activity.project_id.name,
                'flat': activity.flat_id.id,
                'flat_name': activity.flat_id.name,
                'tower_id': activity.tower_id.id,
                'tower_name': activity.tower_id.name,
                'floor_id': activity.floor_id.id,
                'floor_name': activity.floor_id.name,
                'overall_remarks': activity.overall_remarks or '',
                'overall_images': image_urls,
                'line_data': line_data,
                'color': color,
                'wi_status': reject,
            })

        data['list_checklist_data'] = list_checklist_data
        # _logger.info("-gimage_urlsimage_urls----,%s", str(data))

        # data['color'] = color

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist info Fetch', 'checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    # AAAAAA overall remark - 2 images -

    @restapi.method([(["/maker/checklist/update"], "POST")], auth="user")
    def update_checklist_maker(self):
        pr_act_ty_img_obj = self.env['project.activity.type.image']
        # maker will update the checklist and click on submit button notification should sent to res. checker
        seq_no = 0
        params = request.params
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        # _logger.info("---------update_checklist_maker---------,%s", params)
        user_id = False
        send_notification = False
        if params.get('is_draft'):
            # _logger.info("---------params--------,%s", params)
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))
        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        seq_no = activity_type_id.seq_no

        try:
            if params.get('overall_images'):
                images = params.get('overall_images')
                data = []
                for img in images:
                    temp = {'activity_type_id': activity_type_id.id,
                            'overall_img': img, 'img_type': 'pat'}
                    data.append(temp)
                if data:
                    pr_act_ty_img_obj.create(data)
        except Exception as e:
            _logger.info("---exception- overall_images-----,%s", str(e))
            pass

        if activity_type_id and user_id:
            activity_type_id.user_maker = user_id

        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})

                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                # print ("--image_datas---",image_datas)
                # _logger.info("----- No -------,%s",send_notification)

                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'maker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    # _logger.info("----- image datas -------,%s",len(image_datas))

                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    # _logger.info("----- image_urls -------,%s",len(image_urls))

                    for url in image_urls:
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        # user_id = int(params.get('user_id')) or False
        # submitting form and sending notification

        if send_notification:
            activity_type_id.sudo().button_submit(seq_no, user_id)
        # Maintining Log Details
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/checklist/reject"], "POST")], auth="user")
    def update_checklist_reject_checker(self):
        # Checker reject the checklist , notification to maker
        params = request.params
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        # _logger.info("---------update_checklist_reject_checker---------,%s", params)

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        # user_id = int(params.get('user_id')) or False
        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        seq_no = activity_type_id.seq_no
        if activity_type_id and user_id:
            activity_type_id.user_checker = user_id
        # _logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    # seq_no = checklist_id.activity_type_id.seq_no
                    # _logger.info("-----seq_no-------,%s",seq_no)

                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)

                data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'checker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                        'is_pass': line.get('is_pass'),
                        'reason': line.get('reason'), 'seq_no': seq_no,
                        'overall_remarks': activity_type_id.overall_remarks}
                pcl_log = self.env['project.checklist.line.log'].create(data)
                for image in image_datas:
                    image_id = self.env['ir.attachment'].create(
                        {'datas': image, 'name': 'image'})
                    pcl_log.write({'image_ids': [(4, image_id.id)]})
                for url in image_urls:
                    _logger.info("-----url checker reject------,%s", url)
                    self.env['project.checklist.line.log.line'].create(
                        {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        activity_type_id.sudo().button_set_to_maker(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/checklist/update"], "POST")], auth="user")
    def update_checklist_checker(self):
        # this method will get call from checekr to updte the checklist and submit. notification to approver
        params = request.params
        seq_no = False
        user_id = False
        send_notification = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass
        # _logger.info("---------update_checklist_checker---------,%s", params)

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        if activity_type_id and user_id:
            activity_type_id.user_checker = user_id

        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        seq_no = activity_type_id.seq_no
        # if activity_type_id.activity_id and user_id:
        #     activity_type_id.activity_id.user_checker = user_id
        # _logger.info("-----seq_no-------,%s",seq_no)
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                # print('-------overall_remarks-----\n\n\n\n\n', checklist_id)
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                # if line.get('overall_remarks'):
                #     checklist_id.write({'overall_remarks':line.get('overall_remarks')})
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)

                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'checker', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    for url in image_urls:
                        _logger.info("-checker update----url------,%s", url)
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        # user_id = int(params.get('user_id')) or False
        # submitting form and sending notification
        if send_notification:
            activity_type_id.sudo().button_checking_done(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update', 'status': 'Maker'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/checklist/reject"], "POST")], auth="user")
    def update_checklist_reject(self):
        # Approver will reject the checklist and go bakc to checker
        params = request.params
        # _logger.info("---------update_checklist_reject---------,%s", params)
        seq_no = False
        user_id = False
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        if activity_type_id and user_id:
            activity_type_id.user_approver = user_id
        seq_no = activity_type_id.seq_no
        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})
                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)

                data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'approver', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                        'is_pass': line.get('is_pass'),
                        'reason': line.get('reason'), 'seq_no': seq_no,
                        'overall_remarks': activity_type_id.overall_remarks}
                pcl_log = self.env['project.checklist.line.log'].create(data)
                for image in image_datas:
                    image_id = self.env['ir.attachment'].create(
                        {'datas': image, 'name': 'image'})
                    pcl_log.write({'image_ids': [(4, image_id.id)]})
                _logger.info(
                    "----checker-update--image_urls----,%s", image_urls)

                for url in image_urls:
                    _logger.info("----checker-update------,%s", url)

                    self.env['project.checklist.line.log.line'].create(
                        {'url': url, 'project_checklist_line_log_id': pcl_log.id})

        activity_type_id.sudo().button_set_to_checker(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Approver Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/checklist/update"], "POST")], auth="user")
    def update_checklist_approver(self):
        # approver will update the checklist and notification to admin
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')

        seq_no = False
        params = request.params
        user_id = False
        send_notification = False
        if params.get('is_draft'):
            value = str(params.get('is_draft'))
            if value == 'no':
                send_notification = True
        try:
            if params.get('user_id'):
                user_id = params.get('user_id')
        except:
            pass

        if not params.get('activity_type_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        activity_type_id = self.env['project.activity.type'].sudo().browse(
            int(params.get('activity_type_id')))

        if not activity_type_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Activity type ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        if params.get('overall_remarks'):
            activity_type_id.write(
                {'overall_remarks': params.get('overall_remarks')})
        seq_no = activity_type_id.seq_no

        if activity_type_id and user_id:
            activity_type_id.user_approver = user_id

        if params.get('checklist_line'):
            for line in params.get('checklist_line'):
                image_datas = []
                image_urls = []
                checklist_id = self.env['project.checklist.line'].sudo().browse(
                    int(line.get('line_id')))
                # checklist_id = self.env['project.checklist.line'].sudo().browse(int(line.get('line_id')))
                # if checklist_id:
                #     seq_no = checklist_id.activity_type_id.seq_no
                #     _logger.info("-----seq_no-------,%s",seq_no)
                if checklist_id:
                    checklist_id.write(
                        {'is_pass': line.get('is_pass'), 'submitted': 'false'})
                if line.get('reason'):
                    checklist_id.write({'reason': line.get('reason')})

                if line.get('image_data'):
                    for image_data in line.get('image_data'):
                        attachment_vals_list = []
                        attachment_vals_list.append(
                            (0, 0, {'image': image_data}))
                        # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                        # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                        checklist_id.write({'image_ids': attachment_vals_list})
                        image_datas.append(image_data)
                for img in checklist_id.image_ids:
                    checklist_image_url = base_url + \
                        "/web/image?model=project.checklist.line.images&field=image&id=" + \
                        str(img.id)
                    image_urls.append(checklist_image_url)
                if send_notification:
                    data = {'line_id': int(line.get('line_id')), 'checklist_template_id': checklist_id.checklist_template_id.id, 'role': 'approver', 'status': activity_type_id.status, 'activity_type_id': activity_type_id.id, 'project_id': activity_type_id.project_id.id, 'user_id': user_id,
                            'is_pass': line.get('is_pass'),
                            'reason': line.get('reason'), 'seq_no': seq_no,
                            'overall_remarks': activity_type_id.overall_remarks}
                    pcl_log = self.env['project.checklist.line.log'].create(
                        data)
                    for image in image_datas:
                        image_id = self.env['ir.attachment'].create(
                            {'datas': image, 'name': 'image'})
                        pcl_log.write({'image_ids': [(4, image_id.id)]})
                    for url in image_urls:
                        _logger.info("----approver-update------,%s", url)
                        self.env['project.checklist.line.log.line'].create(
                            {'url': url, 'project_checklist_line_log_id': pcl_log.id})

                # if line.get('image_data'):
                #     for image_data in line.get('image_data'):
                #         attachment_vals_list=[]
                #         attachment_vals_list.append((0,0,{'image': image_data}))
                #         # attachment_id=self.env['ir.attachment'].sudo().create(attachment_vals_list)
                #         # activity_type_id.sudo().message_post(body=body_msg, attachment_ids=attachment_id.ids)
                #         checklist_id.write({'image_ids':attachment_vals_list})
        # submitting form and sending notification
        if send_notification:
            activity_type_id.sudo().button_approve(seq_no, user_id)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/user/location"], "POST")], auth="user")
    def update_location_user(self):
        params = request.params
        if not params.get('lat'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send latitude'}),
                            content_type='application/json;charset=utf-8', status=201)
        if not params.get('long'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send longitude'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env.user.sudo().write({
            'lat': params.get('lat'),
            'longi': params.get('long'),

        })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Location Update'}),
                        content_type='application/json;charset=utf-8', status=200)
    # API FOR OFFLINE

    @restapi.method([(["/get/projects/offline"], "POST")], auth="user")
    def get_project_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        projects = self.env['project.info'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not projects:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Projects Not Found '}),
                            content_type='application/json;charset=utf-8', status=201)

        data = []
        for project in projects:
            image = ''
            if project.image:
                image = base64.b64encode(project.image).decode('utf-8')
            pdata = {'id': project.id, 'name': project.name, 'image': image}
            detail_line = []
            for line in project.project_details_line:
                image = ''
                if line.image:
                    image = base64.b64encode(line.image).decode('utf-8')
                detail_line.append(
                    {'id': line.id, 'name': line.name, 'image': image})
            pdata['details_line'] = detail_line
            data.append(pdata)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Data Fetch', 'project_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/tower/offline"], "POST")], auth="user")
    def get_tower_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Towers Not Found '}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                tdata = {'id': tower.id, 'name': tower.name,
                         'project_id': project_id}
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    tdata['details_line_ids'] = detail_lines[0]
                    data.append(tdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetch', 'tower_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/offline"], "POST")], auth="user")
    def get_floors_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        fdata = {'id': floor.id, 'name': floor.name, 'project_id': project_id,
                                 'tower_id': tower.id, 'details_line_ids': detail_lines[0]}

                        data.append(fdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Floors Data Fetch', 'floor_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/offline"], "POST")], auth="user")
    def get_flats_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        fdata = {'id': flat.id, 'name': flat.name, 'project_id': project_id,
                                 'tower_id': tower.id, 'details_line_ids': detail_lines[0]}
                        data.append(fdata)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Flats Data Fetch', 'flat_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/activities/offline"], "POST")], auth="user")
    def get_floors_activities_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']
        project_activity_obj = self.env['project.activity']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            activity_data = {'id': activity.id, 'name': activity.name, 'project_id': project_id, 'tower_id': tower.id, 'floor_id': floor.id,
                                             'description': activity.description or '', 'write_date': str(activity.write_date), 'details_line_ids': detail_lines[0]}
                            data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Activity Data Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/activities/offline"], "POST")], auth="user")
    def get_flats_activities_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Flats Activity Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_floors_obj = self.env['project.floors']
        project_activity_obj = self.env['project.activity']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            activity_data = {'id': activity.id, 'name': activity.name, 'project_id': project_id, 'tower_id': tower.id, 'flat_id': flat.id,
                                             'description': activity.description or '', 'write_date': str(activity.write_date), 'details_line_ids': detail_lines[0]}
                            data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flat Activity Data Fetch', 'activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/activities/types/offline"], "POST")], auth="user")
    def get_floors_activities_types_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Floors Activity Types Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                activity_data = {'id': activity_type.id, 'name': activity_type.name, 'activity_id': activity.id, 'project_id': project_id, 'tower_id': tower.id, 'floor_id': floor.id, 'write_date': str(
                                    activity.write_date), 'status': activity_type.status, 'progress': activity_type.progress_percentage, 'overall_remarks': activity_type.overall_remarks or '', 'details_line_ids': detail_lines[0]}
                                data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flat Activity Data Fetch', 'floors_activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/activities/types/offline"], "POST")], auth="user")
    def get_flats_activities_types_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Flats Activity Types Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                activity_data = {'id': activity_type.id, 'name': activity_type.name, 'activity_id': activity.id, 'project_id': project_id, 'tower_id': tower.id, 'flat_id': flat.id, 'write_date': str(
                                    activity.write_date), 'status': activity_type.status, 'progress': activity_type.progress_percentage, 'overall_remarks': activity_type.overall_remarks or '', 'details_line_ids': detail_lines[0]}
                                data.append(activity_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Floors Activity Data Fetch', 'flats_activity_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/flats/checklist/offline"], "POST")], auth="user")
    def get_flats_checklist_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Checklist Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_checklist_line_log_obj = self.env['project.checklist.line.log']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for flat in tower.tower_flat_line_id:
                        for activity in flat.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                for checklist in activity_type.checklist_ids:
                                    image_data = []
                                    history = []
                                    log_lines = project_checklist_line_log_obj.search(
                                        [('line_id', '=', checklist.id)])

                                    for line in log_lines:
                                        base64image = []
                                        for irattachmnet in line.image_ids:
                                            base64image.append(
                                                irattachmnet.datas)
                                        history.append({
                                            'id': line.id,
                                            'name': line.checklist_template_id.name,
                                            'reason': line.reason,
                                            'is_pass': line.is_pass,
                                            'name': line.checklist_template_id.name,
                                            'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                                            'update_time': str(line.datetime),
                                            'base64image': base64image,
                                            'submitted': 'false',
                                        })
                                    # need to check checklist.id and checklist.template.id
                                    for image in checklist.image_ids:
                                        image_data.append(base64.b64encode(
                                            image.image).decode('utf-8'))
                                    checklist_data = {'history': history, 'activity_type_id': activity_type.id, 'id': checklist.id, 'name': checklist.checklist_template_id.name, 'activity_id': activity.id, 'project_id': project_id,
                                                      'tower_id': tower.id, 'flat_id': flat.id, 'write_date': str(activity.write_date), 'is_pass': checklist.is_pass, 'image': image_data, 'details_line_ids': detail_lines[0]}
                                    data.append(checklist_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Flats Checklist Data Fetch', 'flats_checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/floors/checklist/offline"], "POST")], auth="user")
    def get_floors_checklist_offline(self):
        params = request.params
        if not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send User ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        towers = self.env['project.tower'].sudo().search(
            [('assigned_to_ids', 'in', params.get('user_id'))])

        if not towers:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Checklist Not Found'}),
                            content_type='application/json;charset=utf-8', status=201)
        data = []
        project_details_obj = self.env['project.details']
        project_checklist_line_log_obj = self.env['project.checklist.line.log']

        for tower in towers:
            if tower.project_id:
                project_id = tower.project_id.id
                detail_lines = project_details_obj.search(
                    [('project_info_id', '=', project_id), ('tower_id', 'in', [tower.id])]).ids
                if detail_lines:
                    for floor in tower.tower_floor_line_id:
                        for activity in floor.activity_ids:
                            for activity_type in activity.activity_type_ids:
                                for checklist in activity_type.checklist_ids:
                                    image_data = []
                                    history = []
                                    log_lines = project_checklist_line_log_obj.search(
                                        [('line_id', '=', checklist.id)])

                                    for line in log_lines:
                                        base64image = []
                                        for irattachmnet in line.image_ids:
                                            base64image.append(
                                                irattachmnet.datas)
                                        history.append({
                                            'id': line.id,
                                            'name': line.checklist_template_id.name,
                                            'reason': line.reason,
                                            'is_pass': line.is_pass,
                                            'name': line.checklist_template_id.name,
                                            'submittedBy': {'id': line.user_id.id, 'name': line.user_id.name, 'role': line.role},
                                            'update_time': str(line.datetime),
                                            'base64image': base64image,
                                            'submitted': 'false',
                                        })
                                    # need to check checklist.id and checklist.template.id
                                    for image in checklist.image_ids:
                                        image_data.append(base64.b64encode(
                                            image.image).decode('utf-8'))
                                    checklist_data = {'history': history, 'activity_type_id': activity_type.id, 'id': checklist.id, 'name': checklist.checklist_template_id.name, 'activity_id': activity.id, 'project_id': project_id,
                                                      'tower_id': tower.id, 'floor_id': floor.id, 'write_date': str(activity.write_date), 'is_pass': checklist.is_pass, 'image': image_data, 'details_line_ids': detail_lines[0]}
                                    data.append(checklist_data)

        return Response(json.dumps({'status': 'SUCCESS', 'message': ' Floors Checklist Data Fetch', 'floors_checklist_data': data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/delete/activity"], "POST")], auth="user")
    def delete_activities(self):
        params = request.params
        # _logger.info("--create_duplicate_activities--params-1233333444-",params)
        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Id Not Found!'}),
                            content_type='application/json;charset=utf-8', status=400)

        actvity = request.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        actvity.activity_type_ids.unlink()
        actvity.unlink()

        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': ' Activity(s) Deleted'}),
            content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/duplicate/activities/create"], "POST")], auth="user")
    def create_duplicate_activities(self):
        params = request.params

        # _logger.info("--create_duplicate_activities--params-1233333444-",params)

        if not params.get('activity_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity Id Not Found!'}),
                            content_type='application/json;charset=utf-8', status=400)
        activity_id = request.env['project.activity'].sudo().browse(
            int(params.get('activity_id')))
        if not activity_id:
            return Response(json.dumps({'status': 'FAILED', 'message': 'Activity ID does not exist'}),
                            content_type='application/json;charset=utf-8', status=400)
        # Get the base name of the activity
        base_name = activity_id.name
        count = activity_id.count

        # _logger.info("--FLAT-121212-",activity_id.flat_id.name)
        # _logger.info("--FLOOR-1212121-",activity_id.floor_id.name)
        f_name = ''
        if activity_id.flat_id:
            for activity in activity_id.flat_id.activity_ids[-1]:
                activity_seq = int(activity.index_no) + 1
                f_name = activity_id.flat_id.name
                building_name = activity_id.flat_id.tower_id.name
                project = activity_id.flat_id.project_id.name

        if activity_id.floor_id:
            for activity in activity_id.floor_id.activity_ids[-1]:
                activity_seq = int(activity.index_no) + 1
                f_name = activity_id.floor_id.name
                building_name = activity_id.floor_id.tower_id.name
                project = activity_id.floor_id.project_id.name

        # Find the next available number suffix
        # duplicate_activities = request.env['project.activity'].sudo().search([('name', 'ilike', base_name)])
        # suffix = len(duplicate_activities)
        # Generate the name for the duplicate activity
        duplicate_name = f"{base_name}_{count}"
        vals = {
            "name": duplicate_name,
            "tower_id": activity_id.tower_id.id if activity_id.tower_id else False,
            "flat_id": activity_id.flat_id.id or False,
            "project_id": activity_id.project_id.id,
            "floor_id": activity_id.floor_id.id or False,
            "project_activity_name_id": activity_id.project_activity_name_id.id,
            "project_activity_id": activity_id.project_activity_id.id,
            "description": activity_id.description,
            # "progress_percentage": activity_id.progress_percentage,
            # "activity_type_ids": [(6, 0, activity_id.activity_type_ids.ids)]
        }
        # activity_type_re = project_activity_type_obj.create(project_activity_type_data)

        duplicate_activity_id = request.env['project.activity'].sudo().create(
            vals)

        for type_data in activity_id.activity_type_ids:
            data = {'activity_id': duplicate_activity_id.id, 'project_actn_id': type_data.project_actn_id.id, 'name': type_data.name, 'project_id': activity_id.project_id.id,
                    'tower_id': activity_id.tower_id.id or False, 'flat_id': activity_id.flat_id.id or False, 'floor_id': activity_id.floor_id.id or False}
            pat_rec = self.env['project.activity.type'].sudo().create(data)
            for checklist in type_data.checklist_ids:
                self.env['project.checklist.line'].sudo().create(
                    {'activity_type_id': pat_rec.id, 'checklist_template_id': checklist.checklist_template_id.id})

        ###
        activity_seq = '001'
        if duplicate_activity_id.name:
            # activity_name = duplicate_activity_id.name[:4].strip()
            activity_name = duplicate_activity_id.name

            duplicate_activity_id.index_no = activity_seq
            new_number = int(activity_seq) + 1
            # activity_seq = '{:03d}'.format(new_number)
            activity_type_seq = '001'
            for activity_type in duplicate_activity_id.activity_type_ids:
                no = 1 + 1
                temp = activity_type_seq
                activity_type.index_no = activity_type_seq
                new_number = int(activity_type_seq) + 1
                activity_type_seq = '{:03d}'.format(new_number)
                activity_type.seq_no = "VB"+"/" + str(project) + "/" + str(
                    building_name) + "/" + str(f_name) + "/" + str(activity_name) + "/" + str(temp)

        activity_id.count = count + 1
        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': f'Duplicate Activity ID {duplicate_activity_id.id} Created'}),
            content_type='application/json;charset=utf-8', status=200)

        # except Exception as e:
        #     _logger.error("An error occurred: %s", str(e))
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'An error occurred'}),
        #                     content_type='application/json;charset=utf-8', status=500)


# Material Inspection


    @restapi.method([(["/maker/mi/update"], "POST")], auth="user")
    def update_mi_maker(self):
        # maker will update the checklist and click on submit button notification should sent to res. checker

        params = request.params
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param(
            'web.base.url', default='http://www.odoo.com?NoBaseUrl')
        # _logger.info("---------update_checklist_maker---------,%s", params)

        if not params.get('mi_id') and not params.get('user_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env['material.inspection'].update_mi_maker(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/mi/reject"], "POST")], auth="user")
    def reject_mi_checker(self):
        # Checker reject the checklist , notification to maker
        params = request.params

        _logger.info("---------reject_mi_checker---------,%s", params)

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        self.env['material.inspection'].sudo().reject_mi_checker(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checker Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/checker/mi/update"], "POST")], auth="user")
    def update_mi_checker(self):
        # this method will get call from checekr to updte the checklist and submit. notification to approver
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        self.env['material.inspection'].sudo().update_mi_checker(params)
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update', 'status': 'success'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/reject"], "POST")], auth="user")
    def reject_mi_approver(self):
        # Approver will reject the checklist and go bakc to checker
        params = request.params
        # _logger.info("---------update_checklist_reject---------,%s", params)

        # _logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].sudo().reject_mi_approver(params)

        # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Approver Rejected'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/approver/mi/update"], "POST")], auth="user")
    def update_mi_approver(self):
        # approver will update the checklist and notification to admin

        params = request.params

        # _logger.info("---------update_checklist_checker---------,%s", params)
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send MI ID'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].sudo().update_mi_approver(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Checklist Update'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/material/inspection"], "POST")], auth="user")
    def get_material_inspection(self):
        # if params contain checked_by(id) will send realted MI data otherwise all MI data.
        response = {}
        params = request.params

        # if  not params.get('tower_id') or not params.get('mi_id'):
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Tower Id'}),
        #                     content_type='application/json;charset=utf-8', status=400)

        mi_data = self.env['material.inspection'].sudo().get_material_inspection(
            params.get('tower_id'), params.get('mi_id'))

        response['material_inspection'] = mi_data
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Data Fetch', 'mi_data': response}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/material/inspection"], "POST")], auth="user")
    def create_material_inspection(self):
        params = request.params
        # _logger.info("--create_duplicate_activities--params-1233333444-",params)
        if not params.get('project_info_id') and not params.get('tower_id') and not params.get('checked_by'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send project, tower id and Checked By(User) Id'}),
                            content_type='application/json;charset=utf-8', status=400)

        self.env['material.inspection'].sudo(
        ).create_material_inspection(params)

        return Response(
            json.dumps(
                {'status': 'SUCCESS', 'message': 'Material Inspection Created'}),
            content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/project/towers"], "POST")], auth="user")
    def get_project_towers(self):
        params = request.params
        if not params.get('project_info_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Project Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        towers = self.env['project.tower'].sudo().get_project_towers(
            int(params.get('project_info_id')))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetch', 'towers': towers}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/mi/checklist"], "POST")], auth="user")
    def get_mi_checklist(self):
        checklist = self.env['mi.checklist'].sudo().get_mi_checklist()

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'MI Checklist Fetched', 'mi_checklist': checklist}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/delete/mi"], "POST")], auth="user")
    def delete_mi(self):
        params = request.params
        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)

        mi_rec = self.env['material.inspection'].browse(
            int(params.get('mi_id'))).unlink()

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection form deleted'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/update/mi"], "POST")], auth="user")
    def update_mi(self):
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        self.env['material.inspection'].update_mi(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Updated Successfully'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/replicate/mi"], "POST")], auth="user")
    def replicate_mi(self):
        params = request.params

        if not params.get('mi_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send Mi Id'}),
                            content_type='application/json;charset=utf-8', status=201)
        mi_id = params.get('mi_id')
        self.env['material.inspection'].replicate(int(mi_id))

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Material Inspection Replicate Successfully'}),
                        content_type='application/json;charset=utf-8', status=200)

    # ForGot Password
    @restapi.method([(["/change_password"], "POST")], auth="user")
    def change_password(self):
        params = request.params

        if not params.get('user_id') and not params.get('old_password') and not params.get('new_password'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please Send User Id, Old Password and New password'}),
                            content_type='application/json;charset=utf-8', status=201)
        user_id = params.get('user_id')
        old_password = params.get('old_password')
        new_password = params.get('new_password')

        user = self.env['res.users'].sudo().browse(int(user_id))
        # if not user.check_password(old_password):
        #     return Response(json.dumps({'status': 'FAILED', 'message': 'Old password in incorrect'}),
        #             content_type='application/json;charset=utf-8', status=200)
        try:
            user.password = new_password
            return Response(json.dumps({'status': 'SUCCESS', 'message': 'password chnaged successfully'}),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as e:
            _logger.info("--change_password --e--", str(e))

            return Response(json.dumps({'status': 'FAILED', 'message': 'Can not change the password'}),
                            content_type='application/json;charset=utf-8', status=200)

    ### Training Report ###

    @restapi.method([(["/get/training/report"], "POST")], auth="user")
    def get_training_report_details(self):

        params = request.params
        response = {}
        traning_report = self.env['training.report'].sudo(
        ).get_training_report_details(params)
        # response['training_data'] = traning_report
        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'tower_data': traning_report}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/create/training/report"], "POST")], auth="user")
    def create_training_report(self):

        params = request.params
        self.env['training.report'].sudo().create_training_report(params)

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Training Report Created'}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/get/towers"], "POST")], auth="user")
    def get_project_tower_flat_nc(self):
        params = request.params
        if not params.get('project_id'):
            return Response(json.dumps({'status': 'FAILED', 'message': 'Please send Project ID'}),
                            content_type='application/json;charset=utf-8', status=201)

        tower_records = self.env['project.tower'].sudo().search(
            [('project_id', '=', params.get('project_id'))])
        tower_data = [{'tower_id': tower.id, 'name': tower.name}
                      for tower in tower_records]

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'tower_data': tower_data}),
                        content_type='application/json;charset=utf-8', status=200)

    # API for activity list: listing all the activities

    @restapi.method([(["/activities"], "POST")], auth="public")
    def get_activities(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name,
                              'activity_id': act.id} for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # API for activity types {pre, post, during}

    @restapi.method([(["/activity/type_names"], "POST")], auth="public")
    def get_activity_type_names(self):
        _logger.info("Fetching activity type names")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            activity_id = data.get('activity_id')
            if not activity_id:
                _logger.warning("Activity ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity ID is required'}

            activity = request.env['project.activity.name'].sudo().browse(
                activity_id)
            if not activity.exists():
                _logger.warning("Activity not found for ID: %s", activity_id)
                return {'status': 'FAILED', 'message': 'Activity not found'}

            activity_type_lines = request.env['project.activity.name.line'].sudo().search([
                ('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_type_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    # API for specific checklines associated to activity and its types

    @restapi.method([(["/activity/checklist"], "POST")], auth="public")
    def get_activity_checklist(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.name.line'].sudo().browse(
                patn_id)
            if not activity_type_name.exists():
                _logger.warning(
                    "Activity Type Name not found for ID: %s", patn_id)
                return {'status': 'FAILED', 'message': 'Activity Type Name not found'}

            checklists = request.env['project.activity.type.name.line'].sudo().search([
                ('patn_id', '=', patn_id)])
            checklist_items = [{'name': chk.checklist_id.name,
                                'id': chk.checklist_id.id} for chk in checklists]

            _logger.info("Successfully fetched checklist items: %s",
                         checklist_items)
            return {'status': 'SUCCESS', 'message': 'Checklist items fetched successfully', 'data': checklist_items}
        except Exception as e:
            _logger.exception("Error fetching checklist items: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching checklist items', 'error': str(e)}


#  for set flag manually
# for projects

    @restapi.method([(["/api/project/info"], "POST")], auth="user")
    def get_project_infolist(self):
        _logger.info("Fetching all projects")

        # try:
        #     projects = request.env['project.info'].sudo().search([])
        #     project_data = [{'project_id': project.id,
        #                      'project_name': project.name} for project in projects]

        #     _logger.info("-----projects------%s", project_data)
        #     return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'projects': project_data}

        # except Exception as e:
        #     _logger.exception("Error fetching activities: %s", str(e))
        #     return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

        project_ids = self.env['project.info'].sudo().search(
            [('assigned_to_ids', 'in', self.env.user.id)])
        project_data = []
        get_param = self.env['ir.config_parameter'].sudo().get_param
        for project in project_ids:
            project_data.append({
                'project_name': project.name,
                'project_id': project.id,
            })

        return Response(json.dumps({'status': 'SUCCESS', 'message': 'Project Fetch', 'projects': project_data}),
                        content_type='application/json;charset=utf-8', status=200)

    @restapi.method([(["/api/tower/info"], "POST")], auth="public")
    def get_tower_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            # Extract project_id
            project_id = data.get('project_id')

            # Validate project_id
            if not project_id:
                _logger.warning("Project ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Project ID'}

            # Fetch tower records based on project_id
            tower_records = request.env['project.tower'].sudo().search(
                [('project_id', '=', project_id)])
            tower_data = [{'tower_id': tower.id, 'tower_name': tower.name}
                          for tower in tower_records]

            # Log fetched data
            # _logger.info("Fetched tower data: %s", tower_data)

            # Return success response
            return {'status': 'SUCCESS', 'message': 'Tower Data Fetched', 'towers': tower_data}

        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    @restapi.method([(["/api/floor/info"], "POST")], auth="public")
    def get_floor_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            # Extract project_id
            tower_id = data.get('tower_id')

            # Validate project_id
            if not tower_id:
                _logger.warning("Tower ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Tower ID'}

            # Fetch tower records based on project_id
            floor_records = request.env['project.floors'].sudo().search(
                [('tower_id', '=', tower_id)])
            floor_data = [{'floor_id': floor.id, 'floor_name': floor.name}
                          for floor in floor_records]

            # Log fetched data
            # _logger.info("Fetched Floor data: %s", floor_data)

            # Return success response
            return {'status': 'SUCCESS', 'message': 'Floor Data Fetched', 'floors': floor_data}
        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    @restapi.method([(["/api/flat/info"], "POST")], auth="public")
    def get_flat_info(self):
        try:
            # Parse JSON payload
            data = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Received request data: %s", data)

            # Extract project_id
            tower_id = data.get('tower_id')

            # Validate project_id
            if not tower_id:
                _logger.warning("Tower ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Please send Tower ID'}

            # Fetch tower records based on project_id
            flat_records = request.env['project.flats'].sudo().search(
                [('tower_id', '=', tower_id)])
            flat_data = [{'flat_id': flat.id, 'flat_name': flat.name}
                         for flat in flat_records]

            # Log fetched data
            _logger.info("Fetched Flat data: %s", flat_data)

            # Return success response
            return {'status': 'SUCCESS', 'message': 'Floor Data Fetched', 'flats': flat_data}
        except Exception as e:
            _logger.exception("Unexpected error occurred")
            return {'status': 'FAILED', 'message': 'An unexpected error occurred', 'error': str(e)}

    @restapi.method([(["/api/activities/info"], "POST")], auth="public")
    def get_activities_info(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name,
                              'activity_id': act.id} for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # API for activity types {pre, post, during}

    @restapi.method([(["/api/activity/type/info"], "POST")], auth="public")
    def get_activity_type_info(self):
        _logger.info("Fetching activity type names")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            activity_id = data.get('activity_id')
            if not activity_id:
                _logger.warning("Activity ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity ID is required'}

            activity = request.env['project.activity.name'].sudo().browse(
                activity_id)
            if not activity.exists():
                _logger.warning("Activity not found for ID: %s", activity_id)
                return {'status': 'FAILED', 'message': 'Activity not found'}

            activity_type_lines = request.env['project.activity.name.line'].sudo().search([
                ('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_type_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    @restapi.method([(["/api/users/list"], "POST")], auth="public")
    def get_project_responsibles(self):
        try:
            # Fetch all partners
            partners = request.env['res.users'].sudo().search([])

            # Prepare the partner data for response
            partner_data = [
                {'id': partner.id, 'name': partner.name, }
                for partner in partners
            ]

            # _logger.info("Fetched project responsible users: %s", partner_data)

            # Return the response
            return {
                'status': 'SUCCESS',
                'message': 'Project responsibles fetched successfully',
                'responsibles': partner_data
            }

        except Exception as e:
            _logger.exception(
                "Error fetching project responsibles: %s", str(e))
            return {
                'status': 'FAILED',
                'message': 'An error occurred while fetching project responsibles',
                'error': str(e)
            }

    # API for specific checklines associated to activity and its types

    @restapi.method([(["/api/activity/checklist/info"], "POST")], auth="public")
    def get_activity_checklist_info(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Received data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                return {'status': 'FAILED', 'message': 'Activity Name Line ID is required'}

            # patn_id is ID of project.activity.name.line
            activity_name_line = request.env['project.activity.name.line'].sudo().browse(
                patn_id)
            if not activity_name_line.exists():
                return {'status': 'FAILED', 'message': 'Activity Name Line not found'}

            # Now get related project.activity.type.name
            activity_type = activity_name_line.patn_id

            # Get checklist lines from project.activity.type.name.line
            checklists = request.env['project.activity.type.name.line'].sudo().search([
                ('patn_id', '=', activity_type.id)])

            checklist_items = [{'name': chk.checklist_id.name,
                                'id': chk.checklist_id.id} for chk in checklists]

            return {'status': 'SUCCESS', 'message': 'Checklist items fetched successfully', 'data': checklist_items}
        except Exception as e:
            _logger.exception("Error fetching checklist items: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching checklist items', 'error': str(e)}

    @restapi.method([(["/api/nc/create"], "POST")], auth="public")
    def create_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC creation called")
            _logger.info("Received JSON request: %s", data)
            _logger.info("Extracted activity_id: %s", data.get('activity_id'))
            # Extract required fields
            project_info_id = data.get('project_id')
            project_tower_id = data.get('tower_id')
            project_floor_id = data.get('floor_id')
            project_flats_id = data.get('flat_id')
            project_activity_id = data.get('activity_id')
            _logger.info("Extracted activity_id: %s", project_activity_id)

            project_act_type_id = data.get('activity_type_id')
            project_check_line_id = data.get('id')
            # _logger.info("Extracted checklist_id: %s",
            #              project_check_line_id.id.checklist_id.name)

            custom_checklist_item = data.get('custom_checklist_item')
            description = data.get('description')
            rectified_image = data.get('rectified_image')
            flag_category = data.get('flag_category')
            project_create_date = data.get('project_create_date')
            project_responsible = data.get('project_responsible_id')
            status = data.get('status')

            # Handle Image Upload

            image_data = None
            rectified_image_data = rectified_image

            if rectified_image_data:
                try:
                    image_data = rectified_image_data.split(',')[1]
                    decoded_image = base64.b64decode(image_data)

                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': 'rectified_image.jpg',
                        'type': 'binary',
                        'datas': base64.b64encode(decoded_image),
                        'res_model': 'manually.set.flag',
                        'res_id': nc.id,
                    })
                except Exception as e:
                    _logger.error(f"Error decoding image: {str(e)}")

            # Create NC record
            nc_values = {
                'project_info_id': project_info_id,
                'project_tower_id': project_tower_id,
                'project_floor_id': project_floor_id,
                'project_flats_id': project_flats_id,
                'project_activity_id': project_activity_id,
                'project_act_type_id': project_act_type_id,
                'project_check_line_id': project_check_line_id,
                'description': description,
                'rectified_image': image_data,
                'flag_category': flag_category,
                'project_create_date': project_create_date,
                'project_responsible': project_responsible,
                'status': status,
            }

            if custom_checklist_item:
                nc_values['custom_checklist_item'] = custom_checklist_item

            nc_values.pop('seq_number', None)
            nc_values['seq_number'] = request.env['ir.sequence'].sudo(
            ).next_by_code('manually.set.flag') or _('New')  # type: ignore

            nc = request.env['manually.set.flag'].sudo().create(nc_values)
            _logger.info("NC created successfully with ID: %s", nc.id)

            # Prepare response data
            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC created successfully.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'project_id': nc.project_info_id.id,
                    'tower_id': nc.project_tower_id.id,
                    'floor_id': nc.project_floor_id.id,
                    'flat_id': nc.project_flats_id.id,
                    'activity_id': nc.project_activity_id.id,
                    'activity_type_id': nc.project_act_type_id.id,
                    'id': nc.project_check_line_id.id,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'rectified_image': rectified_image,
                    'project_create_date': nc.project_create_date,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'custom_checklist': nc.custom_checklist_item
                }
            }

            # Send Notification to Project Responsible
            if nc.project_responsible:
                notification_status = self.send_notification(nc)
                response_data['notification_status'] = notification_status

            return response_data, 201  # HTTP 201 Created

        except Exception as e:
            _logger.error("Error creating NC: %s", e)
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500  # HTTP 500 Internal Server Error

    def send_notification(self, nc):
        """ Sends push notification to the responsible person """
        if not nc.project_responsible:
            return {'error': 'No responsible person assigned'}

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        # Conditional address logic
        if flat_name:
            location_detail = f"flat {flat_name}"
        elif floor_name:
            location_detail = f"floor {floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number
        # Get current user's name
        current_user_name = request.env.user.name if request.env.user else 'Unknown User'

        # Update the message
        message = f"{current_user_name} has created a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f" / {location_detail}"
            message += "."
        title = message

        # Get Push Notification ID
        player_id, user_r = request.env['res.users'].sudo(
        ).get_player_id(nc.project_responsible.id)
        player_ids = [player_id] if player_id else []

        if not player_ids:
            return {'error': 'No push notification ID found for the responsible person'}

        # OneSignal API credentials
        app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
        rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

        # Data to send in the notification
        data = {
            "app_id": app_id,
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        # Convert data to JSON
        data_json = json.dumps(data)

        # URL for OneSignal REST API
        url = "https://onesignal.com/api/v1/notifications"

        # Headers for the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {rest_api_key}"
        }

        # Send the notification
        response = requests.post(url, data=data_json, headers=headers)

        # Log Notification Status
        status = 'sent' if response.status_code == 200 else 'failed'
        request.env['app.notification.log'].sudo().create({
            'title': title if status == 'sent' else f"{title} (Failed)",
            'message': message,
            'res_user_id': nc.project_responsible.id,
            'player_id': player_id,
            'seq_no': seq_no,
            'status': status,
            'table_id': nc.id,
            'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
            'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
        })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

    @restapi.method([(["/api/nc/close"], 'POST')], auth="public")
    def close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called")

            nc_id = data.get('nc_id')
            status = data.get('status')
            image = data.get('image')
            description = data.get('description')

            if not nc_id or status != 'close':
                return {'status': 'error', 'message': 'Invalid NC ID or status'}, 400

            image_data = None
            rimage_data = image

            if rimage_data:
                try:
                    image_data = rimage_data.split(',')[1]
                    decoded_image = base64.b64decode(
                        image_data)

                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': 'image.jpg',
                        'type': 'binary',
                        'datas': base64.b64encode(decoded_image),
                        'res_model': 'manually.set.flag',
                        'res_id': nc.id,
                    })
                except Exception as e:
                    _logger.error(f"Error decoding image: {str(e)}")

            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            # image_data = None
            # if image:
            #     try:
            #         image_data = image.split(',')[1]
            #         decoded_image = base64.b64decode(image_data)

            #         request.env['ir.attachment'].sudo().create({
            #             'name': 'closed_nc_image.jpg',
            #             'type': 'binary',
            #             'datas': base64.b64encode(decoded_image),
            #             'res_model': 'manually.set.flag',
            #             'res_id': nc.id,
            #         })
            #     except Exception as e:
            #         _logger.error(f"Error decoding image: {str(e)}")

            # Update NC status
            nc.write({
                'status': 'close',
                'description': description,
                'image': image_data,
            })

            _logger.info("NC status updated to 'close' with ID: %s", nc.id)

            # Send notification to project responsible
            if nc.project_responsible:
                notification_status = self.send_close_notification(nc)

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC closed successfully.',
                'nc_data': {
                    'seq_number': nc.seq_number,
                    'project_create_date': nc.project_create_date,
                    'project_id': nc.project_info_id.id,
                    'tower_id': nc.project_tower_id.id,
                    'floor_id': nc.project_floor_id.id,
                    'flat_id': nc.project_flats_id.id,
                    'activity_id': nc.project_activity_id.id,
                    'activity_type_id': nc.project_act_type_id.id,
                    'id': nc.project_check_line_id.id,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'rectified_image': nc.rectified_image,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'image': image,
                },
                'notification_status': notification_status if nc.project_responsible else None
            }

            return response_data, 200

        except Exception as e:
            _logger.error("Error closing NC: %s", e)
            return {'status': 'error', 'message': f'Failed to close NC: {str(e)}'}, 500

    def send_close_notification(self, nc):
        if not nc.project_responsible and not request.env.user:
            return {'error': 'No recipient found for notification'}

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        seq_no = nc.seq_number
        current_user = request.env.user  # Get the user who is closing the NC
        current_user_name = current_user.name if current_user else 'Unknown User'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        # Conditional address logic
        if flat_name:
            location_detail = f"flat {flat_name}"
        elif floor_name:
            location_detail = f"floor {floor_name}"
        else:
            location_detail = ""

        message = f"{current_user_name} has closed the {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f" / {location_detail}"
            message += "."
        title = message

        # Get player IDs for both project responsible & closing user
        player_ids = []

        # Project Responsible
        if nc.project_responsible:
            project_responsible_player, _ = request.env['res.users'].sudo(
            ).get_player_id(nc.project_responsible.id)
            if project_responsible_player:
                player_ids.append(project_responsible_player)

        # User who closed the NC
        if current_user:
            closing_user_player, _ = request.env['res.users'].sudo(
            ).get_player_id(current_user.id)
            if closing_user_player:
                player_ids.append(closing_user_player)

        if not player_ids:
            return {'error': 'No push notification IDs found for recipients'}

        app_id = "3dbd7654-0443-42a0-b8f1-10f0b4770d8d"
        rest_api_key = "YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"

        data = {
            "app_id": app_id,
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        data_json = json.dumps(data)
        url = "https://onesignal.com/api/v1/notifications"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {rest_api_key}"
        }

        response = requests.post(url, data=data_json, headers=headers)
        status = 'sent' if response.status_code == 200 else 'failed'

        # Log notification for both users
        for user_id in [nc.project_responsible.id, current_user.id]:
            if user_id:
                request.env['app.notification.log'].sudo().create({
                    'title': title if status == 'sent' else f"{title} (Failed)",
                    'message': message,
                    'res_user_id': user_id,
                    'status': status,
                    'seq_no': seq_no,
                    'table_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
                })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}

    @restapi.method([(["/api/nc/fetch_all"], "POST")], auth="public")
    def fetch_all_nc(self):
        try:
            _logger.info("POST API for fetching all NC called")
            _logger.info("Received request at /api/nc/fetch_all")

            # Fetch all tasks
            ncs = request.env['manually.set.flag'].sudo().search([])

            # Prepare response data for all tasks
            nc_data = []
            for nc in ncs:
                _logger.debug("Processing nc ID: %s", nc.id)
                nc_data.append({
                    'seq_number': nc.seq_number,
                    'nc_id': nc.id,
                    'project_info_id': nc.project_info_id.id,
                    'project_info_name': nc.project_info_id.name,
                    'project_tower_id': nc.project_tower_id.id,
                    'project_tower_name': nc.project_tower_id.name,
                    'project_floor_id': nc.project_floor_id.id,
                    'project_floor_name': nc.project_floor_id.name,
                    'project_flats_id': nc.project_flats_id.id,
                    'project_flats_name': nc.project_flats_id.name,

                    'project_activity_id': nc.project_activity_id.id,
                    'project_activity_name': nc.project_activity_id.name,

                    'project_act_type_id': nc.project_act_type_id.id,
                    'project_act_type_name': nc.project_act_type_id.name,

                    'project_check_line_id': nc.project_check_line_id.id,
                    # 'project_check_line_name': nc.project_check_line_id,
                    'project_check_line_name': nc.project_check_line_id.checklist_id.name,
                    # 'project_check_line_name': nc.project_check_line_id.checklist_template_id.name,
                    'custom_checklist_item': nc.custom_checklist_item,

                    'project_create_date': nc.project_create_date,
                    'project_responsible': nc.project_responsible.name,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'rectified_image': nc.rectified_image,
                })

            _logger.info("Total ncs fetched: %s", len(ncs))

            return {
                'status': 'success',
                'ncs': nc_data
            }, 200

        except Exception as e:
            _logger.error("Error fetching ncs: %s", e, exc_info=True)
            return {
                'status': 'error',
                'message': 'Failed to fetch ncs.',
                'error_details': str(e)
            }, 500


def _rotate_session(httprequest):
    if httprequest.session.rotate:
        root.session_store.delete(httprequest.session)
        httprequest.session.sid = root.session_store.generate_key()
        if httprequest.session.uid:
            httprequest.session.session_token = security.compute_session_token(
                httprequest.session, request.env
            )
        httprequest.session.modified = True


SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'phone', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang'}


def generateOTP():
    digits = "0123456789"
    OTP = ""
    for i in range(4):
        OTP += digits[int(math.floor(random.random() * 10))]
    return OTP
