#include "borehole1App.h"
#include "Moose.h"
#include "AppFactory.h"
#include "ModulesApp.h"
#include "MooseSyntax.h"

InputParameters
borehole1App::validParams()
{
  InputParameters params = MooseApp::validParams();
  params.set<bool>("use_legacy_material_output") = false;
  params.set<bool>("use_legacy_initial_residual_evaluation_behavior") = false;
  return params;
}

borehole1App::borehole1App(InputParameters parameters) : MooseApp(parameters)
{
  borehole1App::registerAll(_factory, _action_factory, _syntax);
}

borehole1App::~borehole1App() {}

void
borehole1App::registerAll(Factory & f, ActionFactory & af, Syntax & syntax)
{
  ModulesApp::registerAllObjects<borehole1App>(f, af, syntax);
  Registry::registerObjectsTo(f, {"borehole1App"});
  Registry::registerActionsTo(af, {"borehole1App"});

  /* register custom execute flags, action syntax, etc. here */
}

void
borehole1App::registerApps()
{
  registerApp(borehole1App);
}

/***************************************************************************************************
 *********************** Dynamic Library Entry Points - DO NOT MODIFY ******************************
 **************************************************************************************************/
extern "C" void
borehole1App__registerAll(Factory & f, ActionFactory & af, Syntax & s)
{
  borehole1App::registerAll(f, af, s);
}
extern "C" void
borehole1App__registerApps()
{
  borehole1App::registerApps();
}
