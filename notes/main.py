import os
import webapp2

from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template


###############################################################################
# We'll just use this convenience function to retrieve and render a template.
def render_template(handler, templatename, templatevalues={}):
    path = os.path.join(os.path.dirname(__file__), 'templates/' + templatename)
    html = template.render(path, templatevalues)
    handler.response.out.write(html)


###############################################################################
# This function is for convenience - we'll use it to generate some general
# page parameters.
def get_params():
    result = {}
    user = users.get_current_user()
    if user:
        result['logout_url'] = users.create_logout_url('/')
        result['user'] = user.email()
        result['upload_url'] = blobstore.create_upload_url('/upload')
        # redirect to /upload once blobstore takes object
    else:
        result['login_url'] = users.create_login_url()
    return result


###############################################################################
def get_filtered_notes(filter):
    result = list()
    q = MyImage.query()
    for i in q.fetch():
        if i.school == filter:
            result.append(i)
    return result


###############################################################################
class MainHandler(webapp2.RequestHandler):
    def get(self):
        params = get_params()
        render_template(self, 'index.html', params)


###############################################################################
class ImagesHandler(webapp2.RequestHandler):
    def get(self):
        params = get_params()

        # first we retrieve the images for the current user
        q = MyImage.query(MyImage.user == params['user'])
        result = list()
        for i in q.fetch():
            # we append each image to the list
            result.append(i)

        # we will pass this image list to the template
        params['images'] = result
        params['num_notes'] = len(result)
        render_template(self, 'images.html', params)


###############################################################################
class ImageHandler(webapp2.RequestHandler):
    def get(self):
        params = get_params()
        # we'll get the ID from the request
        image_id = self.request.get('id')

        # this will allow us to retrieve it from NDB
        my_image = ndb.Key(urlsafe=image_id).get()

        # we'll set some parameters and pass this to the template
        params['image_id'] = image_id
        params['image_name'] = my_image.name
        params['image_description'] = my_image.description
        params['image_school'] = my_image.school
        params['image_professor'] = my_image.professor
        render_template(self, 'image.html', params)


class MyImageHandler(webapp2.RequestHandler):
    def get(self):
        params = get_params()
        # we'll get the ID from the request
        image_id = self.request.get('id')

        # this will allow us to retrieve it from NDB
        my_image = ndb.Key(urlsafe=image_id).get()

        # we'll set some parameters and pass this to the template
        params['image_id'] = image_id
        params['image_name'] = my_image.name
        params['image_description'] = my_image.description
        params['image_school'] = my_image.school
        params['image_professor'] = my_image.professor
        render_template(self, 'my_image.html', params)


###############################################################################
class FileUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        params = get_params()
        error_msg = ''

        if params['user']:
            upload_files = self.get_uploads()
            for blob_info in upload_files:
                # blob_info = upload_files[0]
                type = blob_info.content_type

                # we want to make sure the upload is a known type.
                if type in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']:
                    name = self.request.get('name')
                    description = self.request.get('description')
                    school = self.request.get('school')
                    professor = self.request.get('professor')
                    my_image = MyImage()
                    my_image.name = name
                    my_image.description = description
                    my_image.school = school
                    my_image.professor = professor
                    my_image.user = params['user']

                    my_image.image = blob_info.key()
                    my_image.put()
                    image_id = my_image.key.urlsafe()  # key for the object that can be passed around
                    self.redirect('/image?id=' + image_id)
                else:
                    error_msg += "File type not accepted (accepted types: jpeg, png, gif, webp)"



###############################################################################

class ImageManipulationHandler(webapp2.RequestHandler):
    def get(self):

        image_id = self.request.get("id")
        my_image = ndb.Key(urlsafe=image_id).get()
        blob_key = my_image.image
        img = images.Image(blob_key=blob_key)

        modified = False

        h = self.request.get('height')
        w = self.request.get('width')
        fit = False

        if self.request.get('fit'):
            fit = True

        if h and w:
            img.resize(width=int(w), height=int(h), crop_to_fit=fit)
            modified = True

        optimize = self.request.get('opt')
        if optimize:
            img.im_feeling_lucky()
            modified = True

        flip = self.request.get('flip')
        if flip:
            img.vertical_flip()
            modified = True

        mirror = self.request.get('mirror')
        if mirror:
            img.horizontal_flip()
            modified = True

        rotate = self.request.get('rotate')
        if rotate:
            img.rotate(int(rotate))
            modified = True

        result = img
        if modified:
            result = img.execute_transforms(output_encoding=images.JPEG)

        self.response.headers['Content-Type'] = 'image/jpeg'
        self.response.out.write(result)

###############################################################################


class AllImagesHandler(webapp2.RequestHandler):
    def get(self):
        params = get_params()

        # first we retrieve the images for the current user
        q = MyImage.query()
        image_result = list()
        school_result = list()
        name_result = list()
        professor_result = list()

        for i in q.fetch():
            image_result.append(i)
            if i.school not in school_result:
                school_result.append(i.school)
            if i.name not in name_result:
                name_result.append(i.name)
            if i.professor not in professor_result:
                professor_result.append(i.professor)

        params['schools'] = school_result
        params['names'] = name_result
        params['professors'] = professor_result
        params['images'] = image_result

        render_template(self, 'all_images.html', params)


class DeleteHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        image_id = self.request.get('id')
        ndb.Key(urlsafe=image_id).delete()
        self.redirect('/images')


def get_note(img):
    key = ndb.Key(urlsafe=img)
    return key.get()


class SaveEditsHandler(webapp2.RequestHandler):
    def post(self):
        name = self.request.get('name')
        school = self.request.get('school')
        professor = self.request.get('professor')
        description = self.request.get('description')
        img = self.request.get('id')

        n = get_note(img)
        n.name = name
        n.school = school
        n.professor = professor
        n.description = description
        n.put()

        params = get_params()

        params['image_id'] = img
        params['image_name'] = name
        params['image_description'] = description
        params['image_school'] = school
        params['image_professor'] = professor

        render_template(self, 'my_image.html', params)


'''def get_filtered_results(notes, filter_type, filter):
    results = list()
    for note in notes:
        if note.filter_type == filter:
            results.append(note)
    return results'''


class FilterHandler(webapp2.RequestHandler):
    def post(self):
        params = get_params()
        params['school_filter'] = self.request.get('school-filter')
        params['name_filter'] = self.request.get('name-filter')
        params['professor_filter'] = self.request.get('professor-filter')

        notes = MyImage.query()
        school_results = list()
        name_results = list()
        professor_results = list()

        for note in notes:
            if params['school_filter'] != "All":
                s_query = MyImage.query(MyImage.school == params['school_filter']).fetch()
                if note.school == params['school_filter']:
                    school_results.append(note)
            else:
                school_results.append(note)
                s_query = MyImage.query().fetch()

        for note in school_results:
            if params['name_filter'] != "All":
                n_query = MyImage.query(MyImage.name == params['name_filter']).fetch()
                if note.name == params['name_filter']:
                    name_results.append(note)
            else:
                name_results.append(note)
                n_query = MyImage.query().fetch()

        for note in name_results:
            if params['professor_filter'] != "All":
                p_query = MyImage.query(MyImage.professor == params['professor_filter']).fetch()
                if note.professor == params['professor_filter']:
                    professor_results.append(note)
            else:
                professor_results.append(note)
                p_query = MyImage.query().fetch()

        # print("Number of filtered results: " + str(len(professor_results)))

        params['images'] = professor_results

        school_result = list()
        name_result = list()
        professor_result = list()

        a_query = list()

        for s in s_query:
            for n in n_query:
                for p in p_query:
                    if s == n == p:
                        a_query.append(s)

        for i in a_query:
            if i.school not in school_result:
                school_result.append(i.school)
            if i.name not in name_result:
                name_result.append(i.name)
            if i.professor not in professor_result:
                professor_result.append(i.professor)

        params['schools'] = school_result
        params['names'] = name_result
        params['professors'] = professor_result

        render_template(self, 'all_images.html', params)

        '''if filter == "All":
            params = get_params()

            # first we retrieve the images for the current user
            q = MyImage.query()
            image_result = list()
            school_result = list()
            for i in q.fetch():
                # we append each image to the list
                image_result.append(i)
                if i.school not in school_result:
                    school_result.append(i.school)

            params['images'] = image_result
            params['schools'] = school_result

            render_template(self, 'all_images.html', params)
        else:
            params = get_params()

            # first we retrieve the images for the current user
            q = MyImage.query()
            school_result = list()
            for i in q.fetch():
                # we append each image to the list
                if i.school not in school_result:
                    school_result.append(i.school)

            params['schools'] = school_result
            image_result = get_filtered_notes(filter)
            print("filter: " + filter)
            params['images'] = image_result
            render_template(self, 'all_images.html', params)'''


###############################################################################
class MyImage(ndb.Model):
    name = ndb.StringProperty()
    image = ndb.BlobKeyProperty()
    description = ndb.StringProperty()
    school = ndb.StringProperty()
    professor = ndb.StringProperty()
    user = ndb.StringProperty()


###############################################################################
mappings = [
    ('/', MainHandler),
    ('/images', ImagesHandler),
    ('/image', ImageHandler),
    ('/my-image', MyImageHandler),
    ('/upload', FileUploadHandler),
    ('/img', ImageManipulationHandler),
    ('/all-images', AllImagesHandler),
    ('/delete', DeleteHandler),
    ('/save-edits', SaveEditsHandler),
    ('/filter', FilterHandler)
]
app = webapp2.WSGIApplication(mappings, debug=True)
