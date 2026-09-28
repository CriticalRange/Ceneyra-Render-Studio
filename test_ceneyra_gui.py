# -*- coding: utf-8 -*-
"""
Qt automated tests for Ceneyra Render Studio UI (ceneyra_gui.py).
Tests reproduce layout, clipping, usability, and functional defects and verify fixes.
"""

import sys
import unittest
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QPointF

# Ensure QApplication exists for tests
app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

import ceneyra_gui
from ceneyra_gui import CeneyraStudioWindow, PreviewCanvas, ElidedLabel, BatchProcessWorker


class TestCeneyraGuiDefects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.window = CeneyraStudioWindow()
        cls.window.resize(1180, 840)
        cls.window.show()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        app.processEvents()

    def test_01_left_panel_layout_no_clipping(self):
        """
        Defect 1: Left panel was 482px wide minimum, while left_scroll had max width 460px
        and horizontal scrollbar disabled, causing combo_quality and panel right border to clip offscreen.
        Fix ensures left_widget minimumSizeHint fits comfortably within the scroll area.
        """
        left_widget = self.window.left_scroll.widget()
        viewport = self.window.left_scroll.viewport()
        app.processEvents()

        # Left widget minimum size hint must not exceed left_scroll max width
        self.assertLessEqual(
            left_widget.minimumSizeHint().width(),
            self.window.left_scroll.maximumWidth(),
            f"left_widget min width ({left_widget.minimumSizeHint().width()}) exceeds scroll max width ({self.window.left_scroll.maximumWidth()})"
        )

        # Quality combobox must be fully visible inside viewport (not clipped)
        map_tr = self.window.combo_quality.mapTo(viewport, QtCore.QPoint(self.window.combo_quality.width(), 0))
        self.assertLessEqual(
            map_tr.x(),
            viewport.width() + 2,
            f"combo_quality right edge ({map_tr.x()}) is clipped beyond viewport width ({viewport.width()})"
        )

    def test_02_canvas_actual_size_method_exists_and_works(self):
        """
        Defect 2: PreviewCanvas was missing the actual_size() method, causing '1:1' button to do nothing.
        Fix implements actual_size() to set 1:1 pixel mapping and update zoom label to %100.
        """
        canvas = self.window.canvas
        self.assertTrue(
            hasattr(canvas, "actual_size"),
            "PreviewCanvas must implement actual_size() for 1:1 zoom button"
        )

        # Create a mock image
        test_img = QtGui.QImage(400, 400, QtGui.QImage.Format_RGB32)
        test_img.fill(QtGui.QColor("#efba73"))
        tmp_path = ceneyra_gui.CACHE_DIR / "test_actual_size.png"
        test_img.save(str(tmp_path))

        canvas.set_image(str(tmp_path))
        app.processEvents()
        self.assertTrue(canvas.has_image)

        # Click actual size
        canvas.actual_size()
        app.processEvents()

        # Effective scale should be 1.0 (zoom * fit_scale == 1.0)
        effective_scale = canvas.fit_scale() * canvas.zoom
        self.assertAlmostEqual(effective_scale, 1.0, places=2)
        self.assertEqual(self.window.lbl_zoom.text(), "%100")

    def test_03_test_render_does_not_pollute_checkbox_state(self):
        """
        Defect 3: Clicking 'Test Render' permanently set chk_test_mode to Checked,
        locking all subsequent full renders into draft quality (1000x1500, quality 1).
        Fix ensures run_test_render() does not mutate chk_test_mode.
        """
        self.window.chk_test_mode.setChecked(False)

        # Monkey-patch run_full_render to inspect arguments without spawning process
        calls = []
        orig_run_full = self.window.run_full_render
        try:
            self.window.run_full_render = lambda is_quick_test=False: calls.append(is_quick_test)
            self.window.run_test_render()
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0], "run_test_render should pass is_quick_test=True")
            self.assertFalse(
                self.window.chk_test_mode.isChecked(),
                "chk_test_mode must NOT be mutated to checked when clicking Test Render"
            )
        finally:
            self.window.run_full_render = orig_run_full

    def test_04_scene_path_changed_handles_quotes_and_clearing(self):
        """
        Defect 4: on_scene_path_changed didn't handle empty input or quoted non-existent paths properly.
        Fix resets state on empty text and handles quoted / non-existent paths gracefully.
        """
        # Test clearing
        self.window.on_scene_path_changed("")
        self.assertIsNone(self.window.current_scene)
        self.assertEqual(self.window.lbl_scene_size.text(), "Dosya seçilmedi")
        self.assertEqual(self.window.lbl_product_tag.text(), "ÜRÜN: —")

        # Test non-existent file
        self.window.on_scene_path_changed('"C:/non_existent_folder_xyz/file.max"')
        self.assertIsNone(self.window.current_scene)
        self.assertIn("bulunamadı", self.window.lbl_scene_size.text().lower())

    def test_05_busy_state_disables_all_conflicting_controls(self):
        """
        Defect 5: set_busy only disabled 4 buttons, leaving combos, preset buttons,
        and auto_rename active, risking race conditions and duplicate thread spawns.
        """
        self.window.set_busy(True)
        try:
            self.assertFalse(self.window.combo_variant.isEnabled())
            self.assertFalse(self.window.combo_finish.isEnabled())
            self.assertFalse(self.window.combo_camera.isEnabled())
            self.assertFalse(self.window.combo_res.isEnabled())
            self.assertFalse(self.window.combo_quality.isEnabled())
            self.assertFalse(self.window.input_scene.isEnabled())
            self.assertFalse(self.window.combo_part_kapak.isEnabled())
            self.assertFalse(self.window.combo_part_govde.isEnabled())
            self.assertFalse(self.window.combo_part_pleksi.isEnabled())
            self.assertFalse(self.window.combo_part_ayak.isEnabled())
            self.assertFalse(self.window.combo_part_ayak_detay.isEnabled())
            self.assertFalse(self.window.btn_render.isEnabled())
            self.assertEqual(self.window.status_pill.text(), "Meşgul")
        finally:
            self.window.set_busy(False)

        # After releasing busy, controls should be re-enabled
        self.assertTrue(self.window.combo_variant.isEnabled())
        self.assertTrue(self.window.combo_finish.isEnabled())
        self.assertTrue(self.window.btn_render.isEnabled())
        self.assertEqual(self.window.status_pill.text(), "Hazır")

    def test_06_batch_worker_has_cancel_and_stops_process(self):
        """
        Defect 6: BatchProcessWorker lacked cancel/stop functionality.
        Fix adds cancel() to stop running worker and terminate child process cleanly.
        """
        worker = BatchProcessWorker(
            mode="viewport",
            scene_file="dummy.max",
            target_color="WHITE",
            finish_color="GOLD",
            camera_name="default",
            width=100, height=100, quality=1,
            output_path=""
        )
        self.assertTrue(hasattr(worker, "cancel"), "BatchProcessWorker must have cancel() method")
        worker.cancel()
        self.assertTrue(worker._is_cancelled)

    def test_07_output_folder_handles_quotes(self):
        """
        Defect 7: Pasting quoted path into output folder caused Windows path failures.
        Fix strips quotes and ensures directory creation.
        """
        test_dir = ceneyra_gui.RENDERS_DIR
        self.window.input_output.setText(f'"{test_dir}"')
        self.assertEqual(self.window.get_output_dir(), test_dir)

    def test_08_elided_label_minimum_size_hint(self):
        """
        Defect 8: ElidedLabel had default minimumSizeHint width (full text width),
        preventing it from shrinking below 220px in narrow layouts.
        Fix overrides minimumSizeHint to return width 0.
        """
        lbl = ElidedLabel("Very long state message that should be able to shrink and elide in footer")
        self.assertEqual(lbl.minimumSizeHint().width(), 0)

    def test_09_preview_canvas_zoom_anchor_zero_zero(self):
        """
        Defect 9: (anchor or center) evaluated QPointF(0, 0) as falsy in Python,
        falling back incorrectly to center.
        """
        canvas = self.window.canvas
        test_img = QtGui.QImage(400, 400, QtGui.QImage.Format_RGB32)
        test_img.fill(QtGui.QColor("#efba73"))
        tmp_path = ceneyra_gui.CACHE_DIR / "test_zoom.png"
        test_img.save(str(tmp_path))
        canvas.set_image(str(tmp_path))

        canvas.zoom = 1.0
        canvas.pan = QPointF(0, 0)
        # Calling zoom_by with anchor at (0, 0) should respect anchor
        canvas.zoom_by(1.2, QPointF(0, 0))
        self.assertNotEqual(canvas.zoom, 1.0)
        # Offset from center to (0,0) should adjust pan
        self.assertNotEqual(canvas.pan.x(), 0.0)

    def test_10_minimum_window_size_no_clipping(self):
        """Verify that at minimum window dimensions (960x720) no left-panel controls are clipped."""
        self.window.resize(960, 720)
        app.processEvents()
        viewport = self.window.left_scroll.viewport()
        vp_width = viewport.width()

        for combo in self.window.left_scroll.widget().findChildren(QtWidgets.QComboBox):
            if combo.isVisible():
                tr = combo.mapTo(viewport, QtCore.QPoint(combo.width(), 0))
                self.assertLessEqual(
                    tr.x(),
                    vp_width + 2,
                    f"{combo} right edge ({tr.x()}) is clipped beyond viewport ({vp_width}) at minimum size"
                )

    def test_11_preset_buttons_functionality(self):
        """Verify preset buttons switch color and finish comboboxes correctly."""
        self.window.set_preset("ANTHRACITE", "GOLD")
        self.assertEqual(self.window.combo_variant.currentData(), "AA")
        self.assertEqual(self.window.combo_finish.currentData(), "GOLD")

        self.window.set_preset("WHITE", "GOLD")
        self.assertEqual(self.window.combo_variant.currentData(), "BB")
        self.assertEqual(self.window.combo_finish.currentData(), "GOLD")

        self.window.set_preset("ANTHRACITE", "SILVER")
        self.assertEqual(self.window.combo_variant.currentData(), "AA")
        self.assertEqual(self.window.combo_finish.currentData(), "SILVER")

    def test_12_toggle_panels_visibility(self):
        """Verify advanced settings panel and log console toggle open/closed properly."""
        # Advanced settings toggle
        self.assertFalse(self.window.adv_frame.isVisible())
        self.window.toggle_advanced()
        self.assertTrue(self.window.adv_frame.isVisible())
        self.window.toggle_advanced()
        self.assertFalse(self.window.adv_frame.isVisible())

        # Log console toggle
        self.assertFalse(self.window.log_text.isVisible())
        self.window.toggle_log()
        self.assertTrue(self.window.log_text.isVisible())
        self.window.toggle_log()
        self.assertFalse(self.window.log_text.isVisible())

    def test_13_preview_zoom_buttons(self):
        """Verify zoom in and zoom out button actions on canvas."""
        canvas = self.window.canvas
        initial_zoom = canvas.zoom
        canvas.zoom_by(1.25)
        self.assertGreater(canvas.zoom, initial_zoom)
        canvas.zoom_by(1 / 1.25)
        self.assertAlmostEqual(canvas.zoom, initial_zoom, places=2)

    def test_14_canvas_double_click_fits(self):
        """Verify canvas double click resets to fit scale."""
        canvas = self.window.canvas
        canvas.zoom_by(2.0)
        self.assertNotEqual(canvas.zoom, 1.0)
        canvas.fit()
        self.assertEqual(canvas.zoom, 1.0)
        self.assertEqual(canvas.pan.x(), 0.0)
        self.assertEqual(canvas.pan.y(), 0.0)


    def test_15_canvas_rendering_pulse_animation_paints_without_error(self):
        """Regression test: verify PreviewCanvas paints during rendering state without qSin AttributeError or QBackingStore warning."""
        canvas = self.window.canvas
        canvas.set_rendering(True)
        canvas.repaint()
        app.processEvents()
        canvas.set_rendering(False)
        canvas.repaint()
        app.processEvents()

    def test_16_studio_button_working_state_paints_without_error(self):
        """Regression test: verify StudioButton paints during working state without painter leak."""
        btn = self.window.btn_render
        btn.set_working(True)
        btn.repaint()
        app.processEvents()
        btn.set_working(False)
        btn.repaint()
    def test_17_clean_env_strips_qt_variables(self):
        """Verify get_clean_env() removes all QT_ prefixed variables to prevent licensing agent crash."""
        from ceneyra_gui import get_clean_env
        clean = get_clean_env()
        qt_keys = [k for k in clean.keys() if k.upper().startswith("QT_")]
        self.assertEqual(len(qt_keys), 0, f"Found leaked Qt variables in clean_env: {qt_keys}")

    def test_18_open_scene_in_3dsmax_uses_clean_env(self):
        """Verify open_scene_in_3dsmax invokes subprocess.Popen with clean environment."""
        from unittest.mock import patch
        with patch("subprocess.Popen") as mock_popen:
            self.window.current_scene = Path(__file__)  # use existing file
            self.window.open_scene_in_3dsmax()
            self.assertTrue(mock_popen.called)
            _, kwargs = mock_popen.call_args
            env = kwargs.get("env")
            self.assertIsNotNone(env)
            qt_keys = [k for k in env.keys() if k.upper().startswith("QT_")]
            self.assertEqual(len(qt_keys), 0, f"QT_ variables were passed in env: {qt_keys}")

    def test_19_get_windows_short_path(self):
        """Verify get_windows_short_path safely resolves paths and returns valid string."""
        from ceneyra_gui import get_windows_short_path
        p = get_windows_short_path(r"C:\Windows\System32")
        self.assertTrue(len(p) > 0)
        self.assertEqual(get_windows_short_path(""), "")

    def test_20_run_full_render_generates_safe_path_without_error(self):
        """Verify run_full_render constructs clean_prod with re without NameError."""
        from unittest.mock import patch
        self.window.current_scene = Path(__file__)
        self.window.detected_product = "KA1546 TASLAK YENİ"
        with patch.object(ceneyra_gui.BatchProcessWorker, "start"):
            self.window.run_full_render()
            self.assertIsNotNone(self.window.active_worker)
            self.assertIn("KA1546_TASLAK_YEN", self.window.active_worker.output_path)

    def test_21_part_material_combos_sync_and_override(self):
        """Verify part material combos sync with presets and can be overridden individually."""
        self.window.set_preset("ANTHRACITE", "GOLD")
        self.assertEqual(self.window.combo_part_kapak.currentData(), "ANTHRACITE")
        self.assertEqual(self.window.combo_part_govde.currentData(), "ANTHRACITE")
        self.assertEqual(self.window.combo_part_pleksi.currentData(), "GOLD")
        self.assertEqual(self.window.combo_part_kulp.currentData(), "GOLD")
        self.assertEqual(self.window.combo_part_ayak.currentData(), "GOLD")
        self.assertEqual(self.window.combo_part_ayak_detay.currentData(), "GOLD")

        # Now override Kapaklar to OAK
        idx_oak = self.window.combo_part_kapak.findData("OAK")
        self.window.combo_part_kapak.setCurrentIndex(idx_oak)
        self.assertEqual(self.window.combo_part_kapak.currentData(), "OAK")
        self.assertEqual(self.window.combo_part_govde.currentData(), "ANTHRACITE")

    def test_22_open_scene_in_vfb_generates_script_and_launches(self):
        """Verify open_scene_in_vfb writes a valid MAXScript and launches 3ds Max with -U MAXScript."""
        from unittest.mock import patch
        self.assertTrue(hasattr(self.window, "btn_launch_vfb"))
        self.assertTrue(hasattr(self.window, "btn_top_vfb"))
        self.assertTrue(hasattr(self.window, "open_scene_in_vfb"))

        with patch("subprocess.Popen") as mock_popen:
            self.window.current_scene = Path(__file__)
            self.window.open_scene_in_vfb()
            self.assertTrue(mock_popen.called)
            args, kwargs = mock_popen.call_args
            cmd = args[0]
            self.assertIn("-U", cmd)
            self.assertIn("MAXScript", cmd)
            # Verify script was generated and contains vfbControl
            script_path = ceneyra_gui.CACHE_DIR / "open_vray_vfb.ms"
            self.assertTrue(script_path.exists())
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("vfbControl", content)
                self.assertIn("openVFBOnly", content)

    def test_23_btn_batch_dialog_exists_and_opens_dialog(self):
        """Verify btn_batch_dialog exists below btn_render and opens CeneyraBatchDialog."""
        self.assertTrue(hasattr(self.window, "btn_batch_dialog"))
        self.assertEqual(self.window.btn_batch_dialog.text(), "📑  TOPLU RENDER YÖNETİCİSİ (BATCH)")

        self.window.open_batch_dialog()
        app.processEvents()
        self.assertIsNotNone(self.window.batch_dialog)
        self.assertIsInstance(self.window.batch_dialog, ceneyra_gui.CeneyraBatchDialog)
        self.assertTrue(self.window.batch_dialog.isVisible())
        self.window.batch_dialog.close()

    def test_24_batch_dialog_queue_add_and_granular_material_overrides(self):
        """Verify each job in the queue can have independent variant, materials, and camera."""
        dialog = ceneyra_gui.CeneyraBatchDialog(self.window)
        dialog.clear_queue()
        self.assertEqual(len(dialog.queue), 0)

        # Configure Job 1: Antrasit Gövde, Meşe Kapak, Gold Pleksi, PhysCamera001
        idx_oak = dialog.combo_kapak.findData("OAK")
        dialog.combo_kapak.setCurrentIndex(idx_oak)
        idx_anth = dialog.combo_govde.findData("ANTHRACITE")
        dialog.combo_govde.setCurrentIndex(idx_anth)
        idx_gold = dialog.combo_pleksi.findData("GOLD")
        dialog.combo_pleksi.setCurrentIndex(idx_gold)
        idx_cam1 = dialog.combo_camera.findData("PhysCamera001")
        if idx_cam1 >= 0:
            dialog.combo_camera.setCurrentIndex(idx_cam1)

        dialog.add_current_job_to_queue()
        self.assertEqual(len(dialog.queue), 1)
        job1 = dialog.queue[0]
        self.assertEqual(job1["mtl_kapak"], "OAK")
        self.assertEqual(job1["mtl_govde"], "ANTHRACITE")
        self.assertEqual(job1["mtl_pleksi"], "GOLD")
        self.assertIn("PhysCamera001", job1["camera"])

        # Configure Job 2: Beyaz Kapak, Beyaz Gövde, Gümüş Pleksi, PhysCamera002
        idx_w = dialog.combo_kapak.findData("WHITE")
        dialog.combo_kapak.setCurrentIndex(idx_w)
        dialog.combo_govde.setCurrentIndex(idx_w)
        idx_silv = dialog.combo_pleksi.findData("SILVER")
        dialog.combo_pleksi.setCurrentIndex(idx_silv)
        idx_cam2 = dialog.combo_camera.findData("PhysCamera002")
        if idx_cam2 >= 0:
            dialog.combo_camera.setCurrentIndex(idx_cam2)

        dialog.add_current_job_to_queue()
        self.assertEqual(len(dialog.queue), 2)
        job2 = dialog.queue[1]
        self.assertEqual(job2["mtl_kapak"], "WHITE")
        self.assertEqual(job2["mtl_govde"], "WHITE")
        self.assertEqual(job2["mtl_pleksi"], "SILVER")
        self.assertIn("PhysCamera002", job2["camera"])

        # Table rows match queue length and display columns properly
        self.assertEqual(dialog.table_queue.rowCount(), 2)
        # Column 2: Strateji, Column 4: Kamera, Column 5: Gövde / Kapak
        self.assertEqual(dialog.table_queue.item(0, 4).text(), "PhysCamera001")
        self.assertEqual(dialog.table_queue.item(0, 5).text(), "ANTHRACITE / OAK")
        self.assertEqual(dialog.table_queue.item(1, 4).text(), "PhysCamera002")
        self.assertEqual(dialog.table_queue.item(1, 5).text(), "WHITE / WHITE")
        dialog.close()

    def test_25_batch_dialog_output_directory_configuration(self):
        """Verify output directory input reflects custom path and directs render outputs."""
        dialog = ceneyra_gui.CeneyraBatchDialog(self.window)
        custom_out = ceneyra_gui.STUDIO_DIR / "custom_batch_renders"
        dialog.input_output_dir.setText(str(custom_out))

        dialog.add_current_job_to_queue()
        job = dialog.queue[-1]
        self.assertTrue(job["output_path"].startswith(str(custom_out)))
        dialog.close()

    def test_26_batch_dialog_quick_generators(self):
        """Verify 10 variants generator and quick generators populate queue properly."""
        dialog = ceneyra_gui.CeneyraBatchDialog(self.window)
        dialog.queue.clear()
        dialog.refresh_table()

        # Add 10 standard variants
        dialog.add_10_variants_to_queue()
        self.assertEqual(len(dialog.queue), 10)
        presets = [j["preset_tag"] for j in dialog.queue]
        self.assertIn("BB_GOLD", presets)
        self.assertIn("BB_SILVER", presets)
        self.assertIn("AA_GOLD", presets)
        self.assertIn("AA_SILVER", presets)
        self.assertIn("BT_GOLD", presets)
        self.assertIn("BT_SILVER", presets)
        self.assertIn("AT_GOLD", presets)
        self.assertIn("AT_SILVER", presets)
        self.assertIn("SMB_GOLD", presets)
        self.assertIn("SMB_SILVER", presets)

        # Clear queue and test row deletion
        dialog.remove_selected_job()
        self.assertEqual(len(dialog.queue), 10)  # No row selected yet
        dialog.table_queue.selectRow(0)
        dialog.remove_selected_job()
        self.assertEqual(len(dialog.queue), 9)

        dialog.close()

    def test_27_batch_dialog_sequential_execution_and_cancellation(self):
        """Verify sequential batch execution model and cancel behavior."""
        from unittest.mock import patch, MagicMock
        dialog = ceneyra_gui.CeneyraBatchDialog(self.window)
        self.window.current_scene = Path(__file__)
        dialog.queue.clear()
        dialog.add_10_variants_to_queue()
        self.assertEqual(len(dialog.queue), 10)

        # Mock worker so it does not actually run 3ds Max
        with patch.object(ceneyra_gui.BatchProcessWorker, "start") as mock_start:
            dialog.start_batch_rendering()
            self.assertTrue(dialog.is_running)
            self.assertEqual(dialog.current_job_idx, 0)
            self.assertEqual(dialog.queue[0]["status"], "⏳ Render Alınıyor")

            # Cancel execution
            dialog.cancel_batch_rendering()
            self.assertFalse(dialog.is_running)
            self.assertEqual(dialog.queue[0]["status"], "⏹ İptal")

        dialog.close()

    def test_28_batch_dialog_reselect_scene_button_exists(self):
        """Verify 'Sahneyi Tekrar Seç' button exists at the very top of Batch dialog."""
        dialog = ceneyra_gui.CeneyraBatchDialog(self.window)
        self.assertTrue(hasattr(dialog, "btn_reselect_scene"))
        self.assertIn("Sahneyi Tekrar Seç", dialog.btn_reselect_scene.text())
        self.assertTrue(hasattr(dialog, "browse_scene_dialog"))
        dialog.close()

    def test_29_scene_camera_extraction_and_synchronization(self):
        """Verify scene loading extracts camera metadata and populates camera combos."""
        meta_test = ceneyra_gui.CACHE_DIR / "ka1546_meta.json"
        self.assertTrue(meta_test.exists())
        cams = ceneyra_gui.extract_cameras_from_scene_file(meta_test)
        self.assertGreaterEqual(len(cams), 1)

        # Verify load_scene updates camera section in CeneyraStudioWindow
        mock_scene = ceneyra_gui.STUDIO_DIR / "test_scene.max"
        mock_scene.touch()
        try:
            self.window.load_scene(mock_scene)
            self.assertGreaterEqual(self.window.combo_camera.count(), 1)
            self.assertTrue(hasattr(self.window, "lbl_camera_count"))
        finally:
            if mock_scene.exists():
                mock_scene.unlink()

    def test_30_topmost_render_finished_popup_functionality(self):
        """Verify show_topmost_message configures WindowStaysOnTopHint."""
        from unittest.mock import patch
        with patch.object(QtWidgets.QMessageBox, "exec", return_value=QtWidgets.QMessageBox.Ok) as mock_exec:
            res = ceneyra_gui.show_topmost_message(self.window, "Test Title", "Test Message")
            self.assertEqual(res, QtWidgets.QMessageBox.Ok)
            self.assertTrue(mock_exec.called)

    def test_31_rendermask_strategy_recalculation(self):
        """Verify RenderMask strategy assigns Full Render to base and RenderMask to matching subsequent jobs."""
        dialog = ceneyra_gui.CeneyraBatchDialog(self.window)
        dialog.queue.clear()
        dialog.add_10_variants_to_queue()
        self.assertEqual(len(dialog.queue), 10)

        # In 10 standard variants, jobs 0 and 1 share same Govde/Kapak (BB).
        # Job 0 should be "full" and Job 1 should be "mask".
        self.assertEqual(dialog.queue[0]["render_mode"], "full")
        self.assertEqual(dialog.queue[1]["render_mode"], "mask")
        self.assertIn("Full", dialog.table_queue.item(0, 2).text())
        self.assertIn("RenderMask", dialog.table_queue.item(1, 2).text())

        # If RenderMask optimization is unchecked, all jobs become "full"
        dialog.chk_rendermask.setChecked(False)
        self.assertEqual(dialog.queue[0]["render_mode"], "full")
        self.assertEqual(dialog.queue[1]["render_mode"], "full")
        self.assertIn("Full", dialog.table_queue.item(1, 2).text())

        dialog.close()

    def test_32_composite_mask_over_base(self):
        """Verify composite_mask_over_base merges mask over base bitmap."""
        from PySide6.QtGui import QImage, QColor
        base_path = ceneyra_gui.CACHE_DIR / "test_unit_base.png"
        mask_path = ceneyra_gui.CACHE_DIR / "test_unit_mask.png"
        out_path = ceneyra_gui.CACHE_DIR / "test_unit_out.png"

        # Create 100x100 base (red)
        img_base = QImage(100, 100, QImage.Format_ARGB32)
        img_base.fill(QColor(255, 0, 0, 255))
        img_base.save(str(base_path), "PNG")

        # Create 100x100 mask (black with blue circle in center)
        img_mask = QImage(100, 100, QImage.Format_ARGB32)
        img_mask.fill(QColor(0, 0, 0, 255))
        for x in range(40, 60):
            for y in range(40, 60):
                img_mask.setPixelColor(x, y, QColor(0, 255, 0, 255))
        img_mask.save(str(mask_path), "PNG")

        try:
            ok = ceneyra_gui.composite_mask_over_base(base_path, mask_path, out_path)
            self.assertTrue(ok)
            self.assertTrue(out_path.exists())
            result_img = QImage(str(out_path))
            # Center should be green, corner should be red
            self.assertEqual(result_img.pixelColor(50, 50).green(), 255)
            self.assertEqual(result_img.pixelColor(10, 10).red(), 255)
        finally:
            for p in (base_path, mask_path, out_path):
                if p.exists():
                    p.unlink()


if __name__ == "__main__":
    unittest.main()



