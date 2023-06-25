/*
* gWebApp.h
*
*  Created on: Mar 27, 2024
*      Author: Metehan Gezer
*/

#ifndef GWEBAPP_H
#define GWEBAPP_H

#include "gBaseApp.h"

class gWebApp : public gBaseApp {
public:
   gWebApp();
   virtual ~gWebApp();
   gWebApp(int argc, char **argv) = delete;

   /**
	* Called when current activity is invisible.
	* Application will stop rendering after this but will
	* still receive updates.
	*/
   virtual void pause();
   /**
	* Called when current activity is visible again.
	* Application will continue rendering.
	*/
   virtual void resume();

};


#endif //GWEBAPP_H