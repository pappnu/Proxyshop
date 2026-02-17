pragma ComponentBehavior: Bound
import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import qml.components
import qml.dialogs
import qml.views

ApplicationWindow {
    id: appWindow

    property QtObject currentRenderingModel: viewTabBar.currentIndex === 1 ? batchRenderModel : templateListModel

    title: "Proxyshop"
    width: 800
    height: 640
    visible: true
    color: systemPalette.window

    SystemPalette {
        id: systemPalette
    }

    FontLoader {
        id: emojiFontLoader
        source: "file:///C:/Windows/Fonts/seguiemj.ttf"
        //source: "file:///C:/Windows/Fonts/seguisym.ttf"
    }

    FontLoader {
        id: monospaceFontLoader
        source: "file:///C:/Windows/Fonts/CascadiaMono.ttf"
    }

    Settings {
        id: settings

        category: "App"
        location: filePathModel.get_preferences_path("App.ini")

        // UI sizing preferences
        property alias windowWidth: appWindow.width
        property alias windowHeight: appWindow.height
        property alias windowX: appWindow.x
        property alias windowY: appWindow.y
        property int currentRenderModeTab
        property var rootSplitState
        property var templateListSplitState

        // Model preferences
        property string selectedTemplateName
        property string batchModeTemplateSelections
    }

    Component.onCompleted: {
        if (settings.currentRenderModeTab)
            viewTabBar.setCurrentIndex(settings.currentRenderModeTab);

        rootSplit.restoreState(settings.rootSplitState);
        templateListSplit.restoreState(settings.templateListSplitState);

        if (settings.selectedTemplateName)
            templateListModel.select_template(settings.selectedTemplateName);
        if (settings.batchModeTemplateSelections)
            batchRenderModel.restore_template_selections(settings.batchModeTemplateSelections);
    }
    Component.onDestruction: {
        settings.currentRenderModeTab = viewTabBar.currentIndex;

        settings.rootSplitState = rootSplit.saveState();
        settings.templateListSplitState = templateListSplit.saveState();

        settings.selectedTemplateName = templateListModel.selected_template_name();
        settings.batchModeTemplateSelections = batchRenderModel.get_template_selections_json();

        settingsTreeModel.save_configs();
        templateUpdaterModel.save_versions();
    }

    DelegateModel {
        id: templateListDelegateModel
        model: templateListModel
    }

    function updateRenderQueueSize() {
        const rCount = renderOperationsModel.rowCount();
        if (rCount != renderOperationsConnections.renderQueueSize)
            renderOperationsConnections.renderQueueSize = rCount;
    }

    Connections {
        id: renderOperationsConnections

        property int renderQueueSize: 0

        target: renderOperationsModel

        function onRowsInserted() {
            appWindow.updateRenderQueueSize();
        }
        function onRowsRemoved() {
            appWindow.updateRenderQueueSize();
        }
    }

    DropArea {
        anchors.fill: parent
        onDropped: drop => {
            if (drop.hasUrls)
                appWindow.currentRenderingModel.render_targets(drop.urls);
        }
    }

    menuBar: MenuBar {
        id: menuBar

        background.implicitHeight: 0
        background.implicitWidth: 0

        delegate: MenuBarItem {
            id: menuBarItem

            leftPadding: 8
            rightPadding: 8
            topPadding: 7
            bottomPadding: 7
            background: Rectangle {
                color: menuBarItem.down || menuBarItem.highlighted ? systemPalette.text : "transparent"
                opacity: menuBarItem.down ? 0.1 : 0.05
            }
        }

        CustomMenu {
            systemPalette: systemPalette
            title: "File"

            Action {
                text: "Render..."
                onTriggered: appWindow.currentRenderingModel.render_selections()
            }
            MenuSeparator {}
            Action {
                text: "Open app directory"
                onTriggered: Qt.openUrlExternally(filePathModel.app_root)
            }
            Action {
                text: "Open output directory"
                onTriggered: Qt.openUrlExternally(filePathModel.out_directory)
            }
            Action {
                text: "Open templates directory"
                onTriggered: Qt.openUrlExternally(filePathModel.templates_directory)
            }
            Action {
                text: "Open plugins directory"
                onTriggered: Qt.openUrlExternally(filePathModel.plugins_directory)
            }
        }
        CustomMenu {
            systemPalette: systemPalette
            title: "Tools"

            Action {
                text: "Transform images"
                onTriggered: {
                    if (imageTransformLoader.active) {
                        imageTransformLoader.item?.show();
                    } else {
                        imageTransformLoader.active = true;
                    }
                }
            }
            Action {
                text: "Preview system palette"
                onTriggered: {
                    if (systemPaletteViewerLoader.active) {
                        systemPaletteViewerLoader.item?.show();
                    } else {
                        systemPaletteViewerLoader.active = true;
                    }
                }
            }
            Action {
                text: "Preview fonts"
                onTriggered: {
                    if (fontViewerLoader.active) {
                        fontViewerLoader.item?.show();
                    } else {
                        fontViewerLoader.active = true;
                    }
                }
            }
        }
        CustomMenu {
            systemPalette: systemPalette
            title: "Tests"
            implicitWidth: 270

            Action {
                text: "Test all"
                onTriggered: testRendersModel.test_all("", false)
            }
            Action {
                text: "Quick test all"
                onTriggered: testRendersModel.test_all("", true)
            }

            CustomMenu {
                id: testAllLayoutsSubMenu

                systemPalette: systemPalette
                title: "Test all with layout"

                Instantiator {
                    model: testRendersModel.layout_categories

                    delegate: CustomMenuItem {
                        required property int index
                        required property string modelData

                        systemPalette: systemPalette
                        text: modelData
                        onTriggered: testRendersModel.test_all(modelData, false)
                    }

                    onObjectAdded: (index, object) => testAllLayoutsSubMenu.insertItem(index, object)
                    onObjectRemoved: (index, object) => testAllLayoutsSubMenu.removeItem(object)
                }
            }
            CustomMenu {
                id: quickTestAllLayoutsSubMenu

                systemPalette: systemPalette
                title: "Quick test all with layout"

                Instantiator {
                    model: testRendersModel.layout_categories

                    delegate: CustomMenuItem {
                        required property int index
                        required property string modelData

                        systemPalette: systemPalette
                        text: modelData
                        onTriggered: testRendersModel.test_all(modelData, true)
                    }

                    onObjectAdded: (index, object) => quickTestAllLayoutsSubMenu.insertItem(index, object)
                    onObjectRemoved: (index, object) => quickTestAllLayoutsSubMenu.removeItem(object)
                }
            }

            MenuSeparator {}

            Action {
                text: "Test selected template(s)"
                onTriggered: appWindow.currentRenderingModel.test_render("", false)
            }
            Action {
                text: "Quick test selected template(s)"
                onTriggered: appWindow.currentRenderingModel.test_render("", true)
            }

            CustomMenu {
                id: selectedTemplateLayoutsSubMenu

                systemPalette: systemPalette
                title: "Test selected template(s) with layout"

                Instantiator {
                    model: testRendersModel.layout_categories

                    delegate: CustomMenuItem {
                        required property int index
                        required property string modelData

                        systemPalette: systemPalette
                        text: modelData
                        onTriggered: appWindow.currentRenderingModel.test_render(modelData, false)
                    }

                    onObjectAdded: (index, object) => selectedTemplateLayoutsSubMenu.insertItem(index, object)
                    onObjectRemoved: (index, object) => selectedTemplateLayoutsSubMenu.removeItem(object)
                }
            }
            CustomMenu {
                id: selectedTemplateQuickLayoutsSubMenu

                systemPalette: systemPalette
                title: "Quick test selected template(s) with layout"

                Instantiator {
                    model: testRendersModel.layout_categories

                    delegate: CustomMenuItem {
                        required property int index
                        required property string modelData

                        systemPalette: systemPalette
                        text: modelData
                        onTriggered: appWindow.currentRenderingModel.test_render(modelData, true)
                    }

                    onObjectAdded: (index, object) => selectedTemplateQuickLayoutsSubMenu.insertItem(index, object)
                    onObjectRemoved: (index, object) => selectedTemplateQuickLayoutsSubMenu.removeItem(object)
                }
            }
        }

        CustomMenu {
            systemPalette: systemPalette
            title: "Help"

            Action {
                text: `<font face="${emojiFontLoader.name}">🌐</font> Project GitHub`
                onTriggered: Qt.openUrlExternally(github_url)
            }
            Action {
                text: `<font face="${emojiFontLoader.name}">❔</font>  Frequently asked questions`
                onTriggered: Qt.openUrlExternally(`${github_url}#-faq`)
            }
            Action {
                text: `<font face="${emojiFontLoader.name}">🪲</font>  Report an issue`
                onTriggered: Qt.openUrlExternally(`${github_url}/issues`)
            }
        }

        RowLayout {
            parent: menuBar
            anchors.right: parent.right

            CustomButton {
                systemPalette: systemPalette
                text: `<font face="${emojiFontLoader.name}">⬇️</font> Updater`
                onClicked: {
                    if (templateUpdaterLoader.active) {
                        templateUpdaterLoader.item?.show();
                    } else {
                        templateUpdaterLoader.active = true;
                    }
                }
            }
            CustomButton {
                id: settingsButton

                systemPalette: systemPalette
                text: `<font face="${emojiFontLoader.name}">⚙️</font> Settings`
                onClicked: openSettings()

                function openSettings(templateName = "", className = "", pluginName = ""): void {
                    settingsTreeModel.select_settings_section(templateName, className, pluginName);
                    if (settingsWindowLoader.active) {
                        settingsWindowLoader.item?.show();
                    } else {
                        settingsWindowLoader.active = true;
                    }
                }
            }
        }
    }

    CustomMessageDialog {
        id: renderMessageDialog

        dialogContentModel: renderMessageDialogContentModel
    }

    Connections {
        id: renderMessageDialogConnections

        target: renderMessageDialogContentModel
        function onDialogRequested(): void {
            if (renderMessageDialog.visible) {
                renderMessageDialog.accept();
            }
            renderMessageDialog.open();
        }
    }

    CustomFileDialog {
        dialogModel: fileDialogModel
        settings: settings
    }

    Loader {
        id: settingsWindowLoader

        active: false
        asynchronous: true
        onLoaded: item.show()

        Component.onCompleted: {
            setSource("views/SettingsWindow.qml", {
                systemPalette: systemPalette,
                pathModel: filePathModel,
                emojiFontName: emojiFontLoader.name,
                settingsTreeModel: settingsTreeModel,
                settingsModel: settingsModel
            });
        }
    }

    Loader {
        id: templateUpdaterLoader

        active: false
        asynchronous: true
        onLoaded: item.show()

        Component.onCompleted: {
            setSource("views/TemplateUpdater.qml", {
                systemPalette: systemPalette,
                updaterModel: templateUpdaterModel,
                pathModel: filePathModel
            });
        }
    }

    Loader {
        id: renderQueueLoader

        active: false
        asynchronous: true
        onLoaded: item.show()

        Component.onCompleted: {
            setSource("views/RenderQueue.qml", {
                systemPalette: systemPalette,
                emojiFontName: emojiFontLoader.name,
                queueModel: renderOperationsModel,
                pathModel: filePathModel
            });
        }
    }

    Loader {
        id: imageTransformLoader

        active: false
        asynchronous: true
        onLoaded: item.show()

        Component.onCompleted: {
            setSource("tools/ImageTransformWindow.qml", {
                systemPalette: systemPalette,
                transformModel: imageTransformModel
            });
        }
    }

    Loader {
        id: systemPaletteViewerLoader

        active: false
        asynchronous: true
        onLoaded: item.show()

        Component.onCompleted: {
            setSource("tools/SystemPaletteViewer.qml");
        }
    }

    Loader {
        id: fontViewerLoader

        active: false
        asynchronous: true
        onLoaded: item.show()

        Component.onCompleted: {
            setSource("tools/FontViewer.qml");
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: viewTabBar

            Layout.fillWidth: true

            width: parent.width
            implicitHeight: 30
            spacing: 0
            palette.window: systemPalette.mid
            palette.dark: systemPalette.mid
            palette.mid: systemPalette.midlight

            CustomTabButton {
                systemPalette: systemPalette
                text: "Templates"
                implicitHeight: viewTabBar.implicitHeight
                background.implicitHeight: viewTabBar.implicitHeight
            }
            CustomTabButton {
                systemPalette: systemPalette
                text: "Batch mode"
                implicitHeight: viewTabBar.implicitHeight
                background.implicitHeight: viewTabBar.implicitHeight
            }

            RowLayout {
                parent: viewTabBar
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 0

                CustomButton {
                    systemPalette: systemPalette
                    implicitHeight: viewTabBar.implicitHeight
                    text: `<font face="${emojiFontLoader.name}">⏩</font> Queue (${renderOperationsConnections.renderQueueSize})`
                    onClicked: {
                        if (renderQueueLoader.active) {
                            renderQueueLoader.item?.show();
                        } else {
                            renderQueueLoader.active = true;
                        }
                    }
                }
                CustomButton {
                    systemPalette: systemPalette
                    implicitHeight: viewTabBar.implicitHeight
                    text: renderOperationsModel.is_rendering ? `<font face="${emojiFontLoader.name}">🚫</font> Cancel` : `<font face="${emojiFontLoader.name}">⏯️</font> Resume`
                    enabled: renderOperationsConnections.renderQueueSize || renderOperationsModel.is_rendering
                    onClicked: renderOperationsModel.is_rendering ? renderOperationsModel.cancel() : renderOperationsModel.resume()
                }
                CustomButton {
                    id: renderButton

                    systemPalette: systemPalette
                    implicitHeight: viewTabBar.implicitHeight
                    text: `<font face="${emojiFontLoader.name}">▶️</font> Render`
                    onClicked: appWindow.currentRenderingModel.render_selections()
                }
            }
        }

        SplitView {
            id: rootSplit

            Layout.fillHeight: true
            Layout.fillWidth: true

            orientation: Qt.Vertical

            StackLayout {
                SplitView.fillHeight: true
                SplitView.fillWidth: true

                currentIndex: viewTabBar.currentIndex

                Rectangle {
                    color: systemPalette.window
                    Layout.fillHeight: true
                    Layout.fillWidth: true

                    SplitView {
                        id: templateListSplit

                        anchors.fill: parent
                        orientation: Qt.Horizontal

                        TemplateList {
                            SplitView.fillWidth: true
                            SplitView.fillHeight: true

                            systemPalette: systemPalette
                            templateListMdl: templateListModel
                            templateListDelegateMdl: templateListDelegateModel
                            openSettings: settingsButton.openSettings
                        }
                        TemplateDetails {
                            SplitView.minimumWidth: 100
                            SplitView.preferredWidth: 200

                            systemPalette: systemPalette
                            templateListMdl: templateListModel
                            templateListDelegateMdl: templateListDelegateModel
                            pathModel: filePathModel
                        }
                    }
                }
                BatchRenderView {
                    Layout.fillHeight: true
                    Layout.fillWidth: true

                    systemPalette: systemPalette
                    batchModel: batchRenderModel
                    pathModel: filePathModel
                }
            }
            Console {
                SplitView.preferredHeight: 200
                SplitView.fillWidth: true

                systemPalette: systemPalette
                logModel: consoleModel
                pathModel: filePathModel
                emojiFontFamily: emojiFontLoader.name
                monospaceFontFamily: monospaceFontLoader.name
            }
        }
    }
}
