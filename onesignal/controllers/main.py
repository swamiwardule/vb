import base64

import requests
from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

try:
    from cachetools import LRUCache, cachedmethod
except ImportError:
    _logger.debug("Cannot import 'cachetools'.")


class MyController(http.Controller):

    @http.route('/get/activity/details', auth='public', methods=['POST'], csrf=False)
    def get_activity_details(self):
        # _logger.info("---------get_activity_details--------")
        data = json.loads(request.httprequest.data)
        # _logger.info("--------data--------",data)
        # _logger.info("---------projects--------,%s",(data))
        env = request.env
        activity_type_id = int(data['id'])
        activity_data = env['project.activity.type'].sudo(
        ).get_project_activity_details(activity_type_id)
        # _logger.info("---------Activity Data--------,%s",len(activity_data))
        return json.dumps({"status": "SUCCESS", "message": "Activity Data Fetch", "activity_data": activity_data})

    @http.route('/get/user/notifications', auth='public', methods=['POST'], csrf=False)
    def get_users_notification(self):
        # _logger.info("---------get_users_notificaton--------")
        data = json.loads(request.httprequest.data)
        env = request.env
        user_id = int(data['id'])
        Notifications = env['app.notification.log'].sudo(
        ).get_users_notification_details(user_id)
        # _logger.info("---------Notifications--------,%s",len(Notifications))
        return json.dumps({"status": "SUCCESS", "message": "Notification Fetch", "notification_data": Notifications})

    @http.route('/get/all/projects', auth='public', methods=['POST'], csrf=False)
    def get_all_projects(self):
        # _logger.info("---------get_all_projects--------")
        data = json.loads(request.httprequest.data)
        env = request.env
        # _logger.info((env))
        # _logger.info((data['id']))
        user_id = int(data['id'])
        projects = env['project.info'].sudo().get_all_projects_details(user_id)
        # _logger.info("---------projects--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS", "message": "Project Fetch", "project_data": projects})

    @http.route('/get/all/projects/towers/checklist', auth='public', methods=['POST'], csrf=False)
    def get_all_projects_towers_checklist(self):
        data = json.loads(request.httprequest.data)
        env = request.env
        # _logger.info((env))
        # _logger.info((data['id']))
        user_id = int(data['id'])
        # _logger.info("---------get_all_projects_towers_checklist--------")
        projects = env['project.info'].sudo(
        ).get_all_projects_towers_checklist_details(user_id)
        # _logger.info("-------get_all_projects_towers_checklist--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS", "message": "Project Fetch", "tower_info": projects})

    @http.route('/get/all/projects/flats/floors', auth='public', methods=['POST'], csrf=False)
    def get_all_projects_all_flats_floors(self):
        # _logger.info("---------get_all_projects_all_flats_floors--------")

        env = request.env
        data = json.loads(request.httprequest.data)
        env = request.env
        # _logger.info((env))
        # _logger.info((data['id']))
        user_id = int(data['id'])

        projects = env['project.info'].sudo(
        ).get_all_projects_all_flats_floors_details(user_id)
        # _logger.info("---------projects--------,%s",len(projects))
        return json.dumps({"status": "SUCCESS", "message": "Tower info Fetch", "flat_floor_info": projects})

    ##### Need to shift all the above apis to session.py######

    @http.route('/onesignal/my_endpoint', auth='public', methods=['POST'], csrf=False)
    def my_endpoint(self, **kwargs):
        try:
            # Access POST data
            data = json.loads(request.httprequest.data)
            env = request.env
            _logger.info((env))
            _logger.info((data['id']))

            _logger.info((data['token']))
            _logger.info((data['player_id']))
            user_record = env['res.users'].sudo().browse(int(data['id']))
            if user_record:
                child_records = [(0, 0, {'player_id': data['player_id']})]
                user_record.sudo().write({'player_line_ids': child_records})
            # activity_type_id = self.env['project.activity.type'].sudo().browse(int(params.get('activity_type_id')))

            # Process data (you can customize this part)
            result = {"success": True, "message": "Data received successfully"}
        except Exception as e:
            _logger.info(str(e))

            result = {"success": False, "message": str(e)}

        # Return the response as JSON
        return json.dumps(result)

    # API for activity list: listing all the activities

    @http.route('/activities', type='json', auth='public', methods=['POST'], csrf=False)
    def get_activities(self):
        _logger.info("Fetching all activities")
        try:
            activities = request.env['project.activity.name'].sudo().search([])
            activity_list = [{'name': act.name, 'activity_id': act.id}
                             for act in activities]
            # _logger.info("Successfully fetched activities: %s", activity_list)
            return {'status': 'SUCCESS', 'message': 'Activities fetched successfully', 'data': activity_list}
        except Exception as e:
            _logger.exception("Error fetching activities: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activities', 'error': str(e)}

    # API for activity types {pre, post, during}

    @http.route('/activity/type_names', type='json', auth='public', methods=['POST'], csrf=False)
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

            # Fetch activity type names associated with the given activity
            activity_lines = request.env['project.activity.name.line'].sudo().search(
                [('pan_id', '=', activity_id)])
            activity_type_names = [
                {'patn_id': line.patn_id.id, 'name': line.patn_id.name} for line in activity_lines]

            _logger.info("Successfully fetched activity type names: %s",
                         activity_type_names)
            return {'status': 'SUCCESS', 'message': 'Activity type names fetched successfully', 'data': activity_type_names}
        except Exception as e:
            _logger.exception("Error fetching activity type names: %s", str(e))
            return {'status': 'FAILED', 'message': 'Error fetching activity type names', 'error': str(e)}

    # API for specific checklist items associated with activity type

    @http.route('/activity/checklist', type='json', auth='public', methods=['POST'], csrf=False)
    def get_activity_checklist(self):
        _logger.info("Fetching checklist items for activity type")
        try:
            _logger.info("Received request data: %s", request.httprequest.data)
            data = json.loads(request.httprequest.data)
            _logger.info("Parsed JSON data: %s", data)

            patn_id = data.get('patn_id')
            if not patn_id:
                _logger.warning(
                    "Activity Type Name ID is missing in the request")
                return {'status': 'FAILED', 'message': 'Activity Type Name ID is required'}

            activity_type_name = request.env['project.activity.type.name'].sudo().browse(
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


    @http.route('/session/auth/api/nc/fetch', type='json', auth='public', methods=['POST'], csrf=False)
    def fetch_nc_details(self):
        try:
            _logger.info("POST API for fetching NC details called")
            _logger.info("Received request at /api/nc/fetch")
            data = json.loads(request.httprequest.data)
            _logger.info("Parsed JSON data: %s", data)

            # Get nc.id from the request
            nc_id = data.get('nc_id')

            if not nc_id:
                return {
                    'status': 'error',
                    'message': 'NC ID is required.'
                }, 400

            # Fetch the NC record by nc.id
            nc = request.env['manually.set.flag'].sudo().search([('id', '=', nc_id)], limit=1)

            if not nc:
                return {
                    'status': 'error',
                    'message': 'NC not found.'
                }, 404

            # Prepare the response data
            nc_data = {
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
                'project_check_line_name': nc.project_check_line_id.checklist_id.name,
                'custom_checklist_item': nc.custom_checklist_item,
                'project_create_date': nc.project_create_date,
                'project_responsible': nc.project_responsible.name,
                'description': nc.description,
                'flag_category': nc.flag_category,
                'rectified_image': nc.rectified_image,
            }

            _logger.info("NC details fetched: %s", nc_data)

            return {
                'status': 'success',
                'nc': nc_data
            }, 200

        except Exception as e:
            _logger.error("Error fetching NC details: %s", e, exc_info=True)
            return {
                'status': 'error',
                'message': 'Failed to fetch NC details.',
                'error_details': str(e)
            }, 500


    @http.route('/api/nc/submit', type='json', auth='public', methods=['POST'], csrf=False)
    def close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called")

            nc_id = data.get('nc_id')
            status = data.get('status')
            # image = data.get('image')
            overall_remarks = data.get('overall_remarks')


          
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple normal images
            # -------------------------------------------
            image_list = data.get('image', [])
            image_urls = []
            image_errors = []
            
            _logger.info(f"Processing {len(image_list)} normal images for NC ID: {nc.id}")
            
            if image_list and len(image_list) > 0:
                for idx, img in enumerate(image_list[:5]):  # Limit to 5 images
                    try:
                        
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')
                        elif isinstance(img, str):
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'
                        else:
                            error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
                            _logger.error(error_msg)
                            image_errors.append(error_msg)
                            continue
                        
                        if not base64_str:
                            error_msg = f"Image {idx+1}: No data provided"
                            _logger.error(error_msg)
                            image_errors.append(error_msg)
                            continue
                        
                        if not filename or filename.strip() == '':
                            filename = f'image_{idx+1}.jpg'
                        elif '.' not in filename:
                            filename = f'{filename}.jpg'
                        
                        if isinstance(base64_str, str):
                            if 'base64,' in base64_str:
                                base64_str = base64_str.split('base64,')[-1]
                            base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
                        _logger.info(f"Creating image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
                        img_record = request.env['manually.set.flag.images'].sudo().create({
                            'flag_id': nc.id,
                            'image': base64_str,
                            'filename': filename
                        })
                        
                        _logger.info(f"✅ Image record created successfully with ID: {img_record.id}")
                        
                        image_url = f"/web/image/manually.set.flag.images/{img_record.id}/image"
                        image_urls.append({
                            'id': img_record.id,
                            'url': image_url,
                            'filename': filename
                        })
                        
                    except Exception as e:
                        error_msg = f"Image {idx+1} error: {str(e)}"
                        _logger.error(error_msg)
                        _logger.exception(f"Full traceback for image {idx+1}:")
                        image_errors.append(error_msg)
            
            _logger.info(f"Images processed: {len(image_urls)} successful, {len(image_errors)} failed")

            # -------------------------------------------
            # 🔧 IMPROVED: Handle multiple rectified images
            # -------------------------------------------
            rectified_list = data.get('rectified_image', [])
            rectified_urls = []
            rectified_errors = []
            
            _logger.info(f"Processing {len(rectified_list)} rectified images for NC ID: {nc.id}")
            
            if rectified_list and len(rectified_list) > 0:
                for idx, img in enumerate(rectified_list[:5]):  # Limit to 5 images
                    try:
                        # Handle both object format {"data": "...", "filename": "..."} 
                        # and string format "base64string"
                        if isinstance(img, dict):
                            base64_str = img.get('data')
                            filename = img.get('filename', f'image_{idx+1}.jpg')
                        elif isinstance(img, str):
                            # If it's a string, treat it as base64 data directly
                            base64_str = img
                            filename = f'image_{idx+1}.jpg'
                        else:
                            error_msg = f"Image {idx+1}: Invalid format (not dict or string)"
                            _logger.error(error_msg)
                            rectified_errors.append(error_msg)
                            continue
                        
                        # Validate base64 data exists
                        if not base64_str:
                            error_msg = f"Image {idx+1}: No data provided"
                            _logger.error(error_msg)
                            rectified_errors.append(error_msg)
                            continue
                        
                        # Ensure filename has proper extension
                        if not filename or filename.strip() == '':
                            filename = f'image_{idx+1}.jpg'
                        elif '.' not in filename:
                            filename = f'{filename}.jpg'
                        
                        # Clean base64 string - remove data URI prefix if present
                        if isinstance(base64_str, str):
                            # Remove 'data:image/...;base64,' prefix
                            if 'base64,' in base64_str:
                                base64_str = base64_str.split('base64,')[-1]
                            # Remove any whitespace and newlines
                            base64_str = base64_str.strip().replace('\n', '').replace('\r', '')
                        
                        _logger.info(f"Creating rectified image record {idx+1}: filename={filename}, data_length={len(base64_str)}")
                        
                        # Create rectified image record
                        rect_record = request.env['manually.set.flag.rectified.images'].sudo().create({
                            'flag_id': nc.id,
                            'rectified_image': base64_str,
                            'filename': filename
                        })
                        
                        _logger.info(f"✅ Rectified image record created successfully with ID: {rect_record.id}")
                        
                        # Generate URL for the rectified image
                        rectified_url = f"/web/image/manually.set.flag.rectified.images/{rect_record.id}/rectified_image"
                        rectified_urls.append({
                            'id': rect_record.id,
                            'url': rectified_url,
                            'filename': filename
                        })
                        
                    except Exception as e:
                        error_msg = f"Rectified image {idx+1} error: {str(e)}"
                        _logger.error(error_msg)
                        _logger.exception(f"Full traceback for rectified image {idx+1}:")
                        rectified_errors.append(error_msg)
            
            _logger.info(f"Rectified images processed: {len(rectified_urls)} successful, {len(rectified_errors)} failed")


          
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            # image_data = None
            # rimage_data = image

            # if rimage_data:
            #     try:
            #         image_data = rimage_data.split(',')[1]
            #         decoded_image = base64.b64decode(
            #             image_data)

            #         attachment = self.env['ir.attachment'].sudo().create({
            #             'name': 'image.jpg',
            #             'type': 'binary',
            #             'datas': base64.b64encode(decoded_image),
            #             'res_model': 'manually.set.flag',
            #             'res_id': nc.id,
            #         })
            #     except Exception as e:
            #         _logger.error(f"Error decoding image: {str(e)}")


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
                'status': 'submit',
                'overall_remarks': overall_remarks,
                # 'image': image_urls,
            })

            _logger.info("NC status updated to 'submit' with ID: %s", nc.id)

            # Send notification to project responsible
            # if nc.project_responsible:

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
                    'overall_remarks': nc.overall_remarks,
                    'flag_category': nc.flag_category,
                    'rectified_image': nc.rectified_image,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'image': nc.image_urls,
                },
                'notification_status': notification_status
            }
            _logger.info("response data: %s", response_data)

            return response_data, 200

        except Exception as e:
            _logger.error("Error submitting NC: %s", e)
            return {'status': 'error', 'message': f'Failed to submit NC: {str(e)}'}, 500

    def send_close_notification(self, nc):
        _logger.info("=== Sending Approver Notification for NC ID %s ===", nc.id)

        tower = nc.project_tower_id
        if not tower or not tower.assigned_to_ids:
            _logger.error("No assigned users found for tower. Cannot find approvers.")
            return {"error": "No approvers found"}

        approver_users = []

        # 🔍 EXACT SAME LOGIC AS button_checking_done (group.name == 'Approver')
        for user in tower.assigned_to_ids:
            for group in user.groups_id:
                if group.name == "Approver":
                    approver_users.append(user)

        _logger.info("Approvers Found: %s", [u.name for u in approver_users])

        if not approver_users:
            _logger.error("No Approver users assigned to this tower.")
            return {"error": "Approver not assigned to tower"}

        # Build Notification Message
        current_user = request.env.user
        seq_no = nc.seq_number
        
        project_name = nc.project_info_id.name or ''
        tower_name = nc.project_tower_id.name or ''
        category = nc.flag_category or ''

        message = f"{current_user.name} has submitted the {category} for {project_name}/{tower_name}."
        title = f"NC {seq_no} Submitted"

        notification_obj = request.env['app.notification']
        log_obj = request.env['app.notification.log']

        sent = False
        failed_users = []

        # 🔔 Send to all approvers
        for approver in approver_users:
            player_id, _ = request.env['res.users'].sudo().get_player_id(approver.id)

            if player_id:
                try:
                    notification_obj.send_push_notification(
                        title,
                        [player_id],
                        message,
                        [approver.id],
                        seq_no,
                        'close_nc',
                        nc
                    )
                    sent = True

                    log_obj.sudo().create({
                        'title': title,
                        'message': message,
                        'res_user_id': approver.id,
                        'status': "sent",
                        'seq_no': seq_no,
                        'table_id': nc.id,
                        'project_info_id': nc.project_info_id.id,
                        'tower_id': nc.project_tower_id.id
                    })
                except Exception as e:
                    _logger.error("Failed sending to %s: %s", approver.name, e)
                    failed_users.append(approver.name)
            else:
                failed_users.append(approver.name)

        if not sent:
            return {"error": f"No notifications sent. Failed for {failed_users}"}

        return {"success": True, "message": "Notifications sent to approver(s)"}


    # def create_nc(self):
    #     try:
    #         data = json.loads(request.httprequest.data)
    #         _logger.info("POST API for NC creation called")
    #         _logger.info("Received JSON request: %s", data)

    #         # Extract required fields
    #         project_info_id = data.get('project_id')
    #         project_tower_id = data.get('tower_id')
    #         project_floor_id = data.get('floor_id')
    #         project_flats_id = data.get('flat_id')
    #         project_activity_id = data.get('activity_id')
    #         project_act_type_id = data.get('activity_type_id')
    #         project_check_line_id = data.get('id')
    #         description = data.get('description')
    #         rectified_image = data.get('rectified_image')
    #         flag_category = data.get('flag_category')
    #         project_create_date = data.get('project_create_date')
    #         project_responsible = data.get('project_responsible_id')
    #         # date, project_responsible

    #         # Decode the base64 image

    #         image_data = None
    #         rectified_image_data = rectified_image

    #         if rectified_image_data:
    #             try:
    #                 image_data = rectified_image_data.split(',')[1]
    #                 decoded_image = base64.b64decode(
    #                     image_data)

    #                 attachment = self.env['ir.attachment'].sudo().create({
    #                     'name': 'rectified_image.jpg',
    #                     'type': 'binary',
    #                     'datas': base64.b64encode(decoded_image),
    #                     'res_model': 'manually.set.flag',
    #                     'res_id': nc.id,
    #                 })
    #             except Exception as e:
    #                 _logger.error(f"Error decoding image: {str(e)}")

    #         # Create a new nc
    #         nc = request.env['manually.set.flag'].sudo().create({
    #             'project_info_id': project_info_id,
    #             'project_tower_id': project_tower_id,
    #             'project_floor_id': project_floor_id,
    #             'project_flats_id': project_flats_id,
    #             'project_activity_id': project_activity_id,
    #             'project_act_type_id': project_act_type_id,
    #             'project_check_line_id': project_check_line_id,
    #             'description': description,
    #             'rectified_image': image_data,
    #             'flag_category': flag_category,
    #             'project_create_date': project_create_date,
    #             'project_responsible': project_responsible,
    #         })
    #         _logger.info("NC created with values: %s", nc.id)

    #         _logger.info("NC created successfully with ID: %s", nc.id)

    #         response_data = {
    #             'status': 'success',
    #             'nc_id': nc.id,
    #             'message': 'NC created successfully.',
    #             'nc_data': {
    #                 'project_id': nc.project_info_id.id,
    #                 'tower_id': nc.project_tower_id.id,
    #                 'floor_id': nc.project_floor_id.id,
    #                 'flat_id': nc.project_flats_id.id,
    #                 'activity_id': nc.project_activity_id.id,
    #                 'activity_type_id': nc.project_act_type_id.id,
    #                 'id': nc.project_check_line_id.id,
    #                 'description': nc.description,
    #                 'flag_category': nc.flag_category,
    #                 'rectified_image': rectified_image,
    #                 'project_create_date': nc.project_create_date,
    #                 'project_responsible': nc.project_responsible
    #             }
    #         }
    #         _logger.info("Response data to be returned: %s", response_data)

    #         return response_data, 201  # HTTP 201 Created

    #     except Exception as e:
    #         _logger.error("Error creating task: %s", e)
    #         return {
    #             'status': 'error',
    #             'message': f'Failed to create task: {str(e)}'
    #         }, 500   # HTTP 500 Internal Server Error



    @http.route('/approver/nc/close', type='json', auth='public', methods=['POST'], csrf=False)
    def approver_close_nc(self):
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("POST API for NC close called")

            nc_id = data.get('nc_id')


            
            nc = request.env['manually.set.flag'].sudo().browse(nc_id)

            if not nc_id:
                return {'status': 'error', 'message': 'NC ID missing'}, 400

            if not nc.exists():
                return {'status': 'error', 'message': 'NC not found'}, 404

            if nc.status != 'submit':
                return {'status': 'error', 'message': 'NC status must be submit'}, 400
                        
            nc.write({
                'status': 'close'
            })

            response_data = {
                'status': 'success',
                'nc_id': nc.id,
                'message': 'NC closed successfully.',
                'nc_data': {
                    'seq_no': nc.seq_number,
                    'description': nc.description,
                    'flag_category': nc.flag_category,
                    'project_id': nc.project_info_id.id if nc.project_info_id else None,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else None,
                    'floor_id': nc.project_floor_id.id if nc.project_floor_id else None,
                    'flat_id': nc.project_flats_id.id if nc.project_flats_id else None,
                    'activity_id': nc.project_activity_id.id if nc.project_activity_id else None,
                    'activity_type_id': nc.project_act_type_id.id if nc.project_act_type_id else None,
                    'project_responsible': nc.project_responsible.id if nc.project_responsible else None,
                    'project_create_date': nc.project_create_date.isoformat() if nc.project_create_date else None,
                    'custom_checklist': nc.custom_checklist_item,
                    'images': nc.image_urls, 
                    'rectified_images': nc.rectified_urls, 
                },
                
            }            

            # Send notification if needed
            if nc.project_responsible:
                try:
                    response_data['notification_status'] = self.send_notification(nc)
                except Exception as e:
                    _logger.error(f"Error sending notification: {str(e)}")
                    response_data['notification_status'] = {'error': str(e)}

            _logger.info(f"✅ NC creation completed successfully.")
            return response_data

        except Exception as e:
            _logger.error("❌ Error creating NC: %s", str(e))
            _logger.exception("Full traceback:")
            return {
                'status': 'error',
                'message': f'Failed to create NC: {str(e)}'
            }, 500

    def send_notification(self, nc):
        """ Sends push notification to NC creator & project responsible """

        project_name = nc.project_info_id.name if nc.project_info_id else 'Unknown Project'
        tower_name = nc.project_tower_id.name if nc.project_tower_id else 'Unknown Tower'
        flag_category = nc.flag_category if nc.flag_category else 'Unknown Category'
        flat_name = nc.project_flats_id.name if nc.project_flats_id else ''
        floor_name = nc.project_floor_id.name if nc.project_floor_id else ''

        current_user = request.env.user
        current_user_name = current_user.name if current_user else 'Unknown User'

        # Conditional address logic
        if flat_name:
            location_detail = f"Flat/{flat_name}"
        elif floor_name:
            location_detail = f"Floor/{floor_name}"
        else:
            location_detail = ""

        seq_no = nc.seq_number

        # 💡 User who created the NC
        creator_user = nc.create_uid
        # creator_name = creator_user.name if creator_user else "Unknown User"

        # 📝 Notification Message
        message = f"{current_user_name} has closed a {flag_category} for {project_name}/{tower_name}"
        if location_detail:
            message += f"/{location_detail}"
        message += "."
        title = message

        # 🎯 Target users
        player_ids = []

        # Project Responsible
        if nc.project_responsible:
            pr_player, _ = request.env['res.users'].sudo().get_player_id(nc.project_responsible.id)
            if pr_player:
                player_ids.append(pr_player)

        # NC Creator
        if creator_user:
            creator_player, _ = request.env['res.users'].sudo().get_player_id(creator_user.id)
            if creator_player:
                player_ids.append(creator_player)

        if not player_ids:
            return {'error': 'No push notification IDs found for recipients'}

        # OneSignal Push
        data = {
            "app_id": "3dbd7654-0443-42a0-b8f1-10f0b4770d8d",
            "include_player_ids": player_ids,
            "contents": {"en": message},
            "headings": {"en": title},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic YzI4ZWQxOWYtY2YyYy00NjM0LTg5NjgtNTliMjVkNGY4NDA3"
        }

        response = requests.post("https://onesignal.com/api/v1/notifications",
                                data=json.dumps(data),
                                headers=headers)

        status = 'sent' if response.status_code == 200 else 'failed'

        # Logging notification for both NC creator & project responsible
        for user in [creator_user, nc.project_responsible]:
            if user:
                request.env['app.notification.log'].sudo().create({
                    'title': title if status == 'sent' else f"{title} (Failed)",
                    'message': message,
                    'res_user_id': user.id,
                    'status': status,
                    'seq_no': seq_no,
                    'table_id': nc.id,
                    'project_info_id': nc.project_info_id.id if nc.project_info_id else False,
                    'tower_id': nc.project_tower_id.id if nc.project_tower_id else False,
                })

        return {'success': True, 'message': 'Notification sent successfully'} if status == 'sent' else {'error': 'Failed to send notification'}


