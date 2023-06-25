/*
* gWebCanvas.h
*
*  Created on: July 27, 2023
*      Author: Metehan Gezer
*/

#ifndef GWEBCANVAS_H
#define GWEBCANVAS_H

#include "gBaseCanvas.h"
#include "gBaseApp.h"

class gWebCanvas : public gBaseCanvas {
public:
   gWebCanvas(gBaseApp* root);
   virtual ~gWebCanvas();

   virtual void deviceOrientationChanged(DeviceOrientation deviceorientation);

   virtual void touchMoved(int x, int y, int fingerId);
   virtual void touchPressed(int x, int y, int fingerId);
   virtual void touchReleased(int x, int y, int fingerId);

   virtual void pause();
   virtual void resume();
private:

};
#endif //GWEBCANVAS_H