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
        image_result = list()
        school_result = list()
        name_result = list()
        professor_result = list()

        # first we retrieve the images for the current user
        q = MyImage.query(MyImage.user == params['user'])
        result = list()
        for i in q.fetch():
            # we append each image to the list
            result.append(i)

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
        params['image_id'] = my_image.key.urlsafe()
        params['image_name'] = my_image.name
        params['image_description'] = my_image.description
        params['image_school'] = my_image.school
        params['image_professor'] = my_image.professor
        params['images'] = my_image.images
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
        params['images'] = my_image.images

        render_template(self, 'my_image.html', params)


###############################################################################
class FileUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        params = get_params()
        error_msg = ''

        if params['user']:
            upload_files = self.get_uploads()
            professor = self.request.get('professor')
            school = self.request.get('school')
            description = self.request.get('description')
            name = self.request.get('name')

            my_image = MyImage()
            my_image.name = name
            my_image.description = description
            my_image.school = school
            my_image.professor = professor
            my_image.user = params['user']
            my_image.num_likes = 0
            for blob_info in upload_files:
                # blob_info = upload_files[0]
                type = blob_info.content_type

                # we want to make sure the upload is a known type.
                if type in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']:
                    my_image.image = blob_info.key()

                    my_image_data = Image()
                    my_image_data.image = blob_info.key()
                    my_image_data.comments = []

                    my_image.images.append(my_image_data)

                my_image.put()
                image_id = my_image.key.urlsafe()
                self.redirect('/image?id=' + image_id)


class AddComment(webapp2.RequestHandler):
   def post(self):
       image_id = self.request.get('id')
       index = int(self.request.get('index'), 10)
       my_image = ndb.Key(urlsafe=image_id).get()

       comment = Comment()
       comment.comment = self.request.get('comment')
       user = users.get_current_user()
       if user:
           comment.user = user.email()

       my_image.images[index].comments.append(comment)
       my_image.put()
       print(my_image.images[index].comments)
       self.redirect('/image?id=' + image_id)

###############################################################################


class ImageManipulationHandler(webapp2.RequestHandler):
    def get(self):

        image_id = self.request.get("id")
        index = int(self.request.get("index"), 10)
        my_image = ndb.Key(urlsafe=image_id).get()
        # print("Index value: " + str(index))
        blob_key = my_image.images[index].image
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
        params['num_notes'] = len(image_result)

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

        # we'll get the ID from the request
        image_id = self.request.get('id')

        # this will allow us to retrieve it from NDB
        my_image = ndb.Key(urlsafe=image_id).get()

        params['image_id'] = img
        params['image_name'] = name
        params['image_description'] = description
        params['image_school'] = school
        params['image_professor'] = professor
        params['images'] = my_image.images

        render_template(self, 'my_image.html', params)


class FilterHandler(webapp2.RequestHandler):
    def post(self):
        params = get_params()
        params['school_filter'] = self.request.get('school-filter')
        params['name_filter'] = self.request.get('name-filter')
        params['professor_filter'] = self.request.get('professor-filter')

        notes = MyImage.query()
        school_results = list()  # list of notes that satisfy the school filter
        name_results = list()  # list of notes that satisfy the school and name filter
        professor_results = list()  # list of notes that satisfy all filters

        for note in notes:  # run through all notes and select those that satisfy the school filter
            if params['school_filter'] != "All":
                s_query = MyImage.query(MyImage.school == params['school_filter']).fetch()
                if note.school == params['school_filter']:
                    school_results.append(note)
            else:  # add all notes to the list if "All" filter is selected
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
        params['num_notes'] = len(professor_results)

        # filter values that still apply
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


class MyFilterHandler(webapp2.RequestHandler):
    def post(self):
        params = get_params()
        params['school_filter'] = self.request.get('school-filter')
        params['name_filter'] = self.request.get('name-filter')
        params['professor_filter'] = self.request.get('professor-filter')

        notes = MyImage.query(MyImage.user == params['user'])
        school_results = list()  # list of notes that satisfy the school filter
        name_results = list()  # list of notes that satisfy the school and name filter
        professor_results = list()  # list of notes that satisfy all filters

        for note in notes:  # run through all notes and select those that satisfy the school filter
            if params['school_filter'] != "All":
                s_query = MyImage.query(MyImage.school == params['school_filter']).fetch()
                if note.school == params['school_filter']:
                    school_results.append(note)
            else:  # add all notes to the list if "All" filter is selected
                school_results.append(note)
                s_query = MyImage.query(MyImage.user == params['user']).fetch()

        for note in school_results:
            if params['name_filter'] != "All":
                n_query = MyImage.query(MyImage.name == params['name_filter']).fetch()
                if note.name == params['name_filter']:
                    name_results.append(note)
            else:
                name_results.append(note)
                n_query = MyImage.query(MyImage.user == params['user']).fetch()

        for note in name_results:
            if params['professor_filter'] != "All":
                p_query = MyImage.query(MyImage.professor == params['professor_filter']).fetch()
                if note.professor == params['professor_filter']:
                    professor_results.append(note)
            else:
                professor_results.append(note)
                p_query = MyImage.query(MyImage.user == params['user']).fetch()

        params['images'] = professor_results 

        # filter values that still apply
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
        params['num_notes'] = len(a_query)

        render_template(self, 'images.html', params)


'''def get_note(img):
    key = ndb.Key(urlsafe=img)
    return key.get()'''

class AddLikeHandler(webapp2.RequestHandler):
    def post(self):
        image_id = self.request.get('id')

        # print("id: ")
        # print(image_id)

        my_image = ndb.Key(urlsafe=image_id).get()
        user = users.get_current_user()
        print("user: ")
        print(user.email())

        like = Like()
        liked = False

        print("BEFORE users who have liked this post: ")
        print(my_image.likes)

        for liked_user in my_image.likes:
            print("liked_user: ")
            print(liked_user)
            if user.email() == liked_user.user:
                liked = True

        if not liked:
            like.user = user.email()
            my_image.likes.append(like)

       # if user.email() not in my_image.likes:
        #     like.user = user.email()
          #   my_image.likes.append(like)

        print("AFTER users who have liked this post: ")
        print(my_image.likes)

        my_image.num_likes = len(my_image.likes)

        print("number of users who have liked this post:")
        print(my_image.num_likes)

        my_image.put()

        self.redirect("/all-images")



'''def post(self):
       image_id = self.request.get('id')
       index = int(self.request.get('index'), 10)
       my_image = ndb.Key(urlsafe=image_id).get()

       comment = Comment()
       comment.comment = self.request.get('comment')
       user = users.get_current_user()
       if user:
           comment.user = user.email()

       my_image.images[index].comments.append(comment)
       my_image.put()
       print(my_image.images[index].comments)
       self.redirect('/image?id=' + image_id)'''


class Comment(ndb.Model):
    comment = ndb.StringProperty()
    user = ndb.StringProperty()


class Like(ndb.Model):
    user = ndb.StringProperty()


class Image(ndb.Model):
    image = ndb.BlobKeyProperty()
    comments = ndb.LocalStructuredProperty(Comment, repeated=True)


###############################################################################
class MyImage(ndb.Model):
    name = ndb.StringProperty()
    image = ndb.BlobKeyProperty()
    likes = ndb.LocalStructuredProperty(Like, repeated=True)
    num_likes = ndb.IntegerProperty()
    images = ndb.LocalStructuredProperty(Image, repeated=True)
    description = ndb.StringProperty()
    school = ndb.StringProperty()
    professor = ndb.StringProperty()
    user = ndb.StringProperty()


###############################################################################
mappings = [
    ('/', MainHandler),
    ('/images', ImagesHandler),
    ('/image', ImageHandler),
    ('/addcomment', AddComment),
    ('/my-image', MyImageHandler),
    ('/upload', FileUploadHandler),
    ('/img', ImageManipulationHandler),
    ('/all-images', AllImagesHandler),
    ('/delete', DeleteHandler),
    ('/save-edits', SaveEditsHandler),
    ('/filter', FilterHandler),
    ('/myfilter', MyFilterHandler),
    ('/add-like', AddLikeHandler)
]
app = webapp2.WSGIApplication(mappings, debug=True)
