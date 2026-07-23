//* This file is part of the MOOSE framework
//* https://www.mooseframework.org
//*
//* All rights reserved, see COPYRIGHT for full restrictions
//* https://github.com/idaholab/moose/blob/master/COPYRIGHT
//*
//* Licensed under LGPL 2.1, please see LICENSE for details
//* https://www.gnu.org/licenses/lgpl-2.1.html
#include "borehole1TestApp.h"
#include "borehole1App.h"
#include "Moose.h"
#include "AppFactory.h"
#include "MooseSyntax.h"

InputParameters
borehole1TestApp::validParams()
{
  InputParameters params = borehole1App::validParams();
  params.set<bool>("use_legacy_material_output") = false;
  params.set<bool>("use_legacy_initial_residual_evaluation_behavior") = false;
  return params;
}

borehole1TestApp::borehole1TestApp(InputParameters parameters) : MooseApp(parameters)
{
  borehole1TestApp::registerAll(
      _factory, _action_factory, _syntax, getParam<bool>("allow_test_objects"));
}

borehole1TestApp::~borehole1TestApp() {}

void
borehole1TestApp::registerAll(Factory & f, ActionFactory & af, Syntax & s, bool use_test_objs)
{
  borehole1App::registerAll(f, af, s);
  if (use_test_objs)
  {
    Registry::registerObjectsTo(f, {"borehole1TestApp"});
    Registry::registerActionsTo(af, {"borehole1TestApp"});
  }
}

void
borehole1TestApp::registerApps()
{
  registerApp(borehole1App);
  registerApp(borehole1TestApp);
}

/***************************************************************************************************
 *********************** Dynamic Library Entry Points - DO NOT MODIFY ******************************
 **************************************************************************************************/
// External entry point for dynamic application loading
extern "C" void
borehole1TestApp__registerAll(Factory & f, ActionFactory & af, Syntax & s)
{
  borehole1TestApp::registerAll(f, af, s);
}
extern "C" void
borehole1TestApp__registerApps()
{
  borehole1TestApp::registerApps();
}
