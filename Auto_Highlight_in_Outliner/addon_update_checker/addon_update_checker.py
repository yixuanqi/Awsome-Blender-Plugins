
import requests
import sys
import bpy
import os
import html
import textwrap
import bpy.utils.previews
import re
from requests.exceptions import ConnectionError
from datetime import datetime
GIST_ID=''
pcoll = bpy.utils.previews.new()
def load_icons():
    my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    pcoll.load("check", os.path.join(my_icons_dir, "checkmark.png"), 'IMAGE')
    pcoll.load("updatered", os.path.join(my_icons_dir, "updatered.png"), 'IMAGE')

def get_addon_name():
    return __package__.replace(".addon_update_checker","")
    if "." in package_name:
        return package_name.split(".")[0]
    else:
        return package_name
def preferences():
    return bpy.context.preferences.addons[get_addon_name()].preferences
def get_current_version():
    addon=get_addon_name()
    return sys.modules[addon].bl_info['version']
    return str(sys.modules[addon].bl_info['version']).replace("(","").replace(")","").replace(", ","")
def get_available_version():
    
    try:
        try:
            r=requests.get('https://api.github.com/gists/' + GIST_ID)
        except ConnectionError as e:
            print("Could not check for updates! No Internet connection!")
            return None,'No Internet'
        results=r.json()
        return str(results['files']['Version Info']['content']).split('\n')[0],"\n".join(str(results['files']['Version Info']['content']).split('\n')[1:]) if len(str(results['files']['Version Info']['content']).split('\n'))>1 else ''
    except Exception as e:
        # print("API Limit reached! Scrapping data manually!")
        try:
            try:
                r=requests.get('https://gist.github.com/' + GIST_ID)
            except ConnectionError as e:
                print("Could not check for updates! No Internet connection!")
                return None,'No Internet'
            results=r.text
            class_str='"blob-code blob-code-inner js-file-line">'
            version_text=results[results.find(class_str)+len(class_str):]
            version_text=version_text[:version_text.index('</td>')]
            final_message=''
            i=2
            class_str=f'"file-version-info-LC{i}" class="blob-code blob-code-inner js-file-line">'
            while class_str in results: 
                
                message=results[results.find(class_str)+len(class_str):]
                message=message[:message.index('</td>')]
                message=html.unescape(message)
                final_message=(final_message+"\n"+message) if final_message else message
                i+=1
                class_str=f'"file-version-info-LC{i}" class="blob-code blob-code-inner js-file-line">'
            return version_text if len(version_text)<16 else None,final_message
        except:
            # print(e)
            return None,''
def convert_to_asci(string):
    return "".join([str(ord(sub)) for sub in string])
def is_update_available():
    
    version,message=get_available_version()
    try:
        if version:
            
            version_tuple=tuple([int(a) if a.isdigit() else a for a in version.replace(" ","").split('.')])
            #version_int=version.replace(".","").replace(",","").replace(" ","")
            if version_tuple>get_current_version():
                return True,version,message
            else: return False,'Could not check!',''
        else: 
            if message!='No Internet':
                print("Invalid Gist ID!")
            return False,'Could not check!',''
    except:
        return False,"Could not Check!",''
def save_time_to_file(filename, time_str):
    with open(filename, 'w+') as file:
        file.write(time_str)

def read_time_from_file(filename):
    with open(filename, 'r') as file:
        return file.read().strip()



def check_for_updates(force=False):
    current_datetime = datetime.now()
    current_time_iso=datetime.now().isoformat()
    if not force:
        if os.path.exists(os.path.join(os.path.dirname(__file__),"last_check.txt")):
            try:
                last_time=read_time_from_file(os.path.join(os.path.dirname(__file__),"last_check.txt"))
                current_time_dt = datetime.fromisoformat(current_time_iso)
                time_from_file_dt = datetime.fromisoformat(last_time)
                if abs((current_time_dt-time_from_file_dt).days)<preferences().check_every_days:
                    # if get_current_version()<tuple([int(a) if a.isdigit() else a for a in preferences().online_version.replace(" ","").split('.')]):
                    #     preferences().update_available=True
                    return
            except:
                pass
        # Format the time and date
        try:
            save_time_to_file(os.path.join(os.path.dirname(__file__),"last_check.txt"),current_time_iso)
        except Exception:
            pass
    
    preferences().last_check_time =current_datetime.strftime("%I:%M %p on %B %d,%Y")
    
    preferences().update_available,preferences().online_version,preferences().update_message=is_update_available()
    

def draw_update_button(layout):
    layout.operator('wm.url_open',text="Open Downloads Page",icon='EXPORT').url=preferences().download_page_url
def draw_update_section_for_prefs(layout,context=None):
    try:
        box=layout.box()
        row=box.row()
        row=row.split(factor=0.3)
        row.label(text="Update Information:")
        row2=row.split(factor=0.8)
        row3=row2.split(factor=0.6,align=True)
        row3.prop(preferences(),'check_on_boot',toggle=True)
        row3.prop(preferences(),'check_every_days')
        row2.prop(preferences(),'check_for_updates',icon='FILE_REFRESH',text='',toggle=True)
        
        if preferences().update_available:
            box.label(text=f"Update is available!(v{preferences().online_version})",icon_value=pcoll['updatered'].icon_id)
            
            update_message = preferences().update_message
            update_message   = re.sub(r"[\n\t\s]*", "", update_message)
            if update_message:
                message_box=box.box()
                message_box.label(text="Update Message:")
                for line in preferences().update_message.split('\n'):
                    lines = textwrap.wrap(line,context.region.width/10 if context else 100, break_long_words=False)
                    for l in lines:
                        message_box.label(text=l)
            box.prop(preferences(),'download_page_url',text="Download Page URL",icon='LINKED')
            draw_update_button(box)
        else:
            box.label(text=f"Addon is Up to Date! (Last Checked at {preferences().last_check_time})" if preferences().last_check_time else f"Addon is Up to Date!",icon_value=pcoll['check'].icon_id)
    except Exception as e:
        print(e)
def draw_update_section_for_panel(layout,context=None):
    try:
        if preferences().update_available:
            box=layout.box()
            box.label(text=f"Update is available!(v{preferences().online_version})",icon_value=pcoll['updatered'].icon_id)
            update_message = preferences().update_message
            update_message   = re.sub(r"[\n\t\s]*", "", update_message)
            if update_message:
                message_box=box.box()
                message_box.label(text="Update Message:")
                for line in preferences().update_message.split('\n'):
                    lines = textwrap.wrap(line,context.region.width/10 if context else 100, break_long_words=False)
                    for l in lines:
                        message_box.label(text=l)
            draw_update_button(box)
        else:
            pass
            #box.label(text="Addon is Up to Date!",icon_value=pcoll['check'].icon_id)
    except Exception as e:
        print(e)
def check_for_updates_toggled(self, context):
    

    # Get current time and date
    
    check_for_updates(force=True)
    if self.check_for_updates:
        self.check_for_updates=False
class AddonUpdateChecker():
    online_version:bpy.props.StringProperty(default='1.0.0')
    update_message:bpy.props.StringProperty(default='')
    download_page_url:bpy.props.StringProperty(default=f"https://blendermarket.com/account/orders_search?orders_search%5Bq%5D={get_addon_name()}",name="Download Page URL")
    update_available:bpy.props.BoolProperty(default=False,name="Update Available")
    check_for_updates:bpy.props.BoolProperty(default=False,name="Check for Updates",update=check_for_updates_toggled)
    check_on_boot:bpy.props.BoolProperty(default=True,name="Check for Updates on Boot!")
    last_check_time:bpy.props.StringProperty(default="")
    check_every_days:bpy.props.IntProperty(default=7,name="Check every X days",description="Check for Updates every X days")
def register(gist_id=''):
    if gist_id:
        global GIST_ID
        GIST_ID=gist_id
    if not pcoll:
        load_icons()
    if preferences().check_on_boot:
        check_for_updates()
def unregister():
    try:
        bpy.utils.previews.remove(pcoll)
    except:
        pass