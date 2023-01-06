package com.li.androidchip8;

import android.content.Context;
import android.util.AttributeSet;
import android.view.SurfaceView;

public class Chip8View extends SurfaceView implements Runnable, Chip8 {

    public Chip8View(Context context) {
        this(context, null);
    }

    public Chip8View(Context context, AttributeSet attrs) {
        this(context, attrs, 0);
    }

    public Chip8View(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
    }

    @Override
    public void loadGame(String gameFilePath) {

    }

    @Override
    public void loop() {

    }

    @Override
    public void onStop() {

    }

    @Override
    public void onResume() {

    }

    @Override
    public void onDestroy() {

    }

    @Override
    public void keyEvent(int index, boolean pressed) {

    }

    @Override
    public void run() {

    }
}
