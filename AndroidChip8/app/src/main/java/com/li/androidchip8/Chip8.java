package com.li.androidchip8;

public interface Chip8 {
    void loadGame(String gameFilePath);

    void loop();

    void onStop();

    void onResume();

    void onDestroy();

    void keyEvent(int index, boolean pressed);
}

enum VMState {
    IDLE,
    RUNNING,
    STOP
}
