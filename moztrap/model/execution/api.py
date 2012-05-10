from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS
from tastypie import fields
from tastypie.authorization import DjangoAuthorization, Authorization
from tastypie.authentication import ApiKeyAuthentication, Authentication

from .models import Run, RunCaseVersion, Result, StepResult
from ..core.api import ProductVersionResource, UserResource
from ..core.auth import User
from ..environments.api import EnvironmentResource
from ..environments.models import Environment
from ..library.api import CaseVersionResource
from ..mtresource import MTModelResource



class RunResource(MTModelResource):
    """ Fetch the test runs for the specified product and version. """

    productversion = fields.ForeignKey(ProductVersionResource, "productversion")
    environments = fields.ToManyField(EnvironmentResource, "environments", full=True)

    class Meta:
        queryset = Run.objects.all()
        fields = [
            "id",
            "name",
            "description",
            "resource_uri",
            "status",
            "productversion",
            "environments",
            "runcaseversions",
            ]
        filtering = {
            "productversion": (ALL_WITH_RELATIONS),
            "status": ("exact"),
        }

    def dehydrate(self, bundle):
        pv = bundle.obj.productversion
        bundle.data['productversion_name'] = pv.version
        bundle.data['product_name'] = pv.product.name

        return bundle

    """
    TODO @@@ Cookbook item for Tastypie docs.
    Want full=false in the list endpoint and full=True in
    the detail endpoint
    """
    def dispatch_detail(self, request, **kwargs):
        """For details, we want the full info on environments for the run """
        self.fields["environments"].full=True
        return super(RunResource, self).dispatch_detail(request, **kwargs)


    def dispatch_list(self, request, **kwargs):
        """For list, we don't want the full info on environments """
        self.fields["environments"].full=False
        return super(RunResource, self).dispatch_list(request, **kwargs)



class RunCaseVersionResource(ModelResource):
    """
    RunCaseVersion represents the connection between a run and a caseversion.

    It is possible to return a result for each runcaseversion.  So the result
    will sit as a peer to the caseversion under the runcaseversion.

    """

    run = fields.ForeignKey(RunResource, "run")
    caseversion = fields.ForeignKey(CaseVersionResource, "caseversion", full=True)

    class Meta:
        queryset = RunCaseVersion.objects.all()
        filtering = {
            "run": (ALL_WITH_RELATIONS),
            "caseversion": (ALL_WITH_RELATIONS),
            }
        fields = {"id", "run", "run_id"}


    def dehydrate(self, bundle):

        # give the id of the run for convenience
        bundle.data["run_id"] = bundle.obj.run.id
        return bundle



class ResultResource(ModelResource):
    environment = fields.ForeignKey(EnvironmentResource, "environment")
    runcaseversion = fields.ForeignKey(RunCaseVersionResource, "runcaseversion")
    tester = fields.ForeignKey(UserResource, "tester")

    class Meta:

        queryset = Result.objects.all()
        resource_name = 'result'
        list_allowed_methods = ['patch']
#        authentication = Authentication()
#        authorization = Authorization()
        authentication = ApiKeyAuthentication()
        authorization = DjangoAuthorization()


    def obj_create(self, bundle, request=None, **kwargs):
        """
        Manually create the proper results objects.

        This is necessary because we have special handler methods for
        setting the statuses which we want to keep DRY.

        """

        data = bundle.data.copy()

        rcv = RunCaseVersion.objects.get(pk=data.pop("runcaseversion"))
        env = Environment.objects.get(pk=data.pop("environment"))
        tester = User.objects.get(pk=data.pop("tester"))
        user = User.objects.get(username=request.GET.get("username"))

        data["user"] = user

        result = Result(
            runcaseversion=rcv,
            environment=env,
            tester=tester,
            created_by=user,
        )
        result.save()

        status_methods = {
            "passed": result.finishsucceed,
            "failed": result.finishfail,
            "invalidated": result.finishinvalidate,
            }

        set_status = status_methods[data.pop("status")]
        set_status(**data)

        bundle.obj = result
        return bundle






"""
Authentication:  use API Key.
    In short term, we create an API key for every user, and they have to ask the admin for that key.
    the admin gets it in the admin console.
    admin goes to the user management page a button to generate api key and copy and email it to the user.

Authorization: need custom class

"""