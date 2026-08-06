# Test output

Real, pasted terminal output from a full local run — not written by hand.
Environment: Windows 11, Python 3.12.10, fresh `pip install -r
requirements-dev.txt`, fresh `db.sqlite3` (deleted and re-migrated
immediately before this run). CI runs the same commands on every push on
Ubuntu with Python 3.11 and 3.12 — see `.github/workflows/ci.yml` and the
Actions tab of the repo for that run's live output.

## `ruff check .`

```
All checks passed!
```

## `python manage.py makemigrations --check --dry-run`

```
No changes detected
```

## `python manage.py migrate`

```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, warehouse
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying sessions.0001_initial... OK
  Applying warehouse.0001_initial... OK
```

## `pytest -v`

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.6.0 -- ...\.venv\Scripts\python.exe
cachedir: .pytest_cache
django: version: 5.1.4, settings: config.settings (from ini)
rootdir: C:\Users\xshan\Desktop\box-selection-system
configfile: pyproject.toml
testpaths: tests
plugins: cov-6.0.0, django-4.9.0
collecting ... collected 77 items

tests/test_api.py::test_health_endpoint PASSED                           [  1%]
tests/test_api.py::test_recommend_happy_path PASSED                      [  2%]
tests/test_api.py::test_recommend_unknown_sku_returns_400 PASSED         [  3%]
tests/test_api.py::test_recommend_empty_items_returns_400 PASSED         [  5%]
tests/test_api.py::test_recommend_no_fit_returns_200_with_no_fit_strategy PASSED [  6%]
tests/test_api.py::test_order_recommend_action_persists_and_updates_status PASSED [  7%]
tests/test_api.py::test_order_recommend_then_fetch_persisted_result PASSED [  9%]
tests/test_api.py::test_order_recommend_with_no_items_returns_400 PASSED [ 10%]
tests/test_api.py::test_fetching_recommendation_before_computing_returns_404 PASSED [ 11%]
tests/test_api.py::test_products_list_endpoint PASSED                    [ 12%]
tests/test_api.py::test_boxes_list_endpoint PASSED                       [ 14%]
tests/test_api.py::test_openapi_schema_is_served PASSED                  [ 15%]
tests/test_management_commands.py::test_seed_demo_data_creates_catalogue_and_orders PASSED [ 16%]
tests/test_management_commands.py::test_seed_demo_data_is_idempotent PASSED [ 18%]
tests/test_management_commands.py::test_seed_demo_data_flush_rebuilds_from_scratch PASSED [ 19%]
tests/test_management_commands.py::test_recommend_box_prints_trace_for_known_order PASSED [ 20%]
tests/test_management_commands.py::test_recommend_box_multi_box_order PASSED [ 22%]
tests/test_management_commands.py::test_recommend_box_no_fit_order PASSED [ 23%]
tests/test_management_commands.py::test_recommend_box_unknown_order_raises_command_error PASSED [ 24%]
tests/test_models.py::test_product_rejects_non_positive_dimensions PASSED [ 25%]
tests/test_models.py::test_product_rejects_zero_weight PASSED            [ 27%]
tests/test_models.py::test_box_rejects_non_positive_dimensions PASSED    [ 28%]
tests/test_models.py::test_product_sku_must_be_unique PASSED             [ 29%]
tests/test_models.py::test_box_code_must_be_unique PASSED                [ 31%]
tests/test_models.py::test_volume_properties PASSED                      [ 32%]
tests/test_models.py::test_order_item_unique_per_product_per_order PASSED [ 33%]
tests/test_models.py::test_order_default_status_is_pending PASSED        [ 35%]
tests/test_services.py::test_order_items_to_domain_items_expands_quantity PASSED [ 36%]
tests/test_services.py::test_cart_lines_to_domain_items_expands_quantity PASSED [ 37%]
tests/test_services.py::test_cart_lines_raises_on_unknown_sku PASSED     [ 38%]
tests/test_services.py::test_recommend_for_order_persists_recommendation_and_updates_status PASSED [ 40%]
tests/test_services.py::test_recommend_for_order_sets_no_fit_status PASSED [ 41%]
tests/test_services.py::test_recommend_for_order_is_idempotent_on_rerun PASSED [ 42%]
tests/test_services.py::test_recommend_ignores_inactive_boxes PASSED     [ 44%]
tests/test_services.py::test_recommend_multi_box_when_no_single_box_fits PASSED [ 45%]
tests/test_web_views.py::test_home_page_lists_orders PASSED              [ 46%]
tests/test_web_views.py::test_home_page_empty_state PASSED               [ 48%]
tests/test_web_views.py::test_visualize_computes_recommendation_on_first_view PASSED [ 49%]
tests/test_web_views.py::test_visualize_reuses_existing_recommendation PASSED [ 50%]
tests/test_web_views.py::test_visualize_renders_svgs_for_single_box PASSED [ 51%]
tests/test_web_views.py::test_visualize_no_fit_order_renders_without_error PASSED [ 53%]
tests/test_web_views.py::test_visualize_multi_box_order_renders_one_card_per_box PASSED [ 54%]
tests/test_web_views.py::test_visualize_unknown_order_returns_404 PASSED [ 55%]
tests/test_dimensions.py::test_dimensions_rejects_non_positive PASSED    [ 57%]
tests/test_dimensions.py::test_volume PASSED                             [ 58%]
tests/test_dimensions.py::test_fits_within_no_rotation PASSED            [ 59%]
tests/test_dimensions.py::test_free_item_has_six_rotations_when_all_sides_differ PASSED [ 61%]
tests/test_dimensions.py::test_cube_has_exactly_one_distinct_rotation PASSED [ 62%]
tests/test_dimensions.py::test_this_side_up_restricts_to_two_rotations PASSED [ 63%]
tests/test_dimensions.py::test_this_side_up_cube_base_has_one_rotation PASSED [ 64%]
tests/test_fit.py::test_volume_is_not_enough_a_rod_does_not_fit_in_a_smaller_volume_cube PASSED [ 66%]
tests/test_fit.py::test_exact_fit_succeeds PASSED                        [ 67%]
tests/test_fit.py::test_item_only_fits_in_one_orientation PASSED         [ 68%]
tests/test_fit.py::test_this_side_up_item_cannot_use_forbidden_rotation PASSED [ 70%]
tests/test_fit.py::test_two_items_pack_side_by_side PASSED               [ 71%]
tests/test_fit.py::test_weight_limit_blocks_placement_even_if_geometry_fits PASSED [ 72%]
tests/test_fit.py::test_partial_pack_reports_correct_unplaced_items PASSED [ 74%]
tests/test_fit.py::test_random_packings_never_violate_geometry_invariants PASSED [ 75%]
tests/test_multibox.py::test_splits_across_multiple_boxes_when_none_hold_everything PASSED [ 76%]
tests/test_multibox.py::test_every_item_placed_exactly_once_across_units PASSED [ 77%]
tests/test_multibox.py::test_unresolved_items_reported_when_something_fits_no_box_at_all PASSED [ 79%]
tests/test_multibox.py::test_respects_max_boxes_safety_cap PASSED        [ 80%]
tests/test_selector.py::test_selects_cheapest_box_that_fits PASSED       [ 81%]
tests/test_selector.py::test_rejects_boxes_too_small_by_weight_before_running_geometry PASSED [ 83%]
tests/test_selector.py::test_rejects_box_when_item_too_large_for_any_rotation PASSED [ 84%]
tests/test_selector.py::test_trace_includes_every_box_in_catalogue PASSED [ 85%]
tests/test_selector.py::test_no_fit_when_nothing_in_catalogue_can_hold_the_order PASSED [ 87%]
tests/test_selector.py::test_tie_break_prefers_higher_utilization_at_equal_cost PASSED [ 88%]
tests/test_selector.py::test_geometric_rejection_when_items_individually_fit_but_not_together PASSED [ 89%]
tests/test_visualizer.py::test_isometric_svg_contains_one_svg_root PASSED [ 90%]
tests/test_visualizer.py::test_isometric_svg_draws_three_faces_per_item PASSED [ 92%]
tests/test_visualizer.py::test_isometric_svg_handles_empty_plan PASSED   [ 93%]
tests/test_visualizer.py::test_color_for_sku_is_deterministic PASSED     [ 94%]
tests/test_visualizer.py::test_color_for_sku_differs_across_skus PASSED  [ 96%]
tests/test_visualizer.py::test_orthographic_svg_draws_one_rect_per_item_plus_container_outline PASSED [ 97%]
tests/test_visualizer.py::test_orthographic_svg_supports_all_three_views PASSED [ 98%]
tests/test_visualizer.py::test_orthographic_svg_empty_plan_still_draws_container PASSED [100%]

============================= 77 passed in 0.92s ==============================
```

## `pytest --cov=packing --cov=warehouse --cov=api --cov-report=term-missing`

```
---------- coverage: platform win32, python 3.12.10-final-0 ----------
Name                                              Stmts   Miss  Cover   Missing
-------------------------------------------------------------------------------
api\__init__.py                                       0      0   100%
api\apps.py                                           5      0   100%
api\management\__init__.py                            0      0   100%
api\management\commands\__init__.py                   0      0   100%
api\serializers.py                                   40      0   100%
api\urls.py                                           8      0   100%
api\views.py                                         56      0   100%
api\visualizer.py                                    70      0   100%
api\web_urls.py                                       3      0   100%
api\web_views.py                                     29      0   100%
packing\__init__.py                                   0      0   100%
packing\dimensions.py                                26      0   100%
packing\entities.py                                  36      0   100%
packing\fit.py                                        51      0   100%
packing\multibox.py                                  43      1    98%   50
packing\selector.py                                  54      1    98%   31
packing\trace.py                                     25      0   100%
warehouse\__init__.py                                 0      0   100%
warehouse\admin.py                                   31      0   100%
warehouse\apps.py                                     5      0   100%
warehouse\management\__init__.py                      0      0   100%
warehouse\management\commands\__init__.py             0      0   100%
warehouse\management\commands\recommend_box.py       34      0   100%
warehouse\management\commands\seed_demo_data.py      32      0   100%
warehouse\migrations\0001_initial.py                  7      0   100%
warehouse\migrations\__init__.py                      0      0   100%
warehouse\models.py                                  68      5    93%   36, 62, 83, 99, 121
warehouse\services.py                                62      0   100%
-------------------------------------------------------------------------------
TOTAL                                               685      7    99%

77 passed in 1.84s
```

The two uncovered lines are `packing/multibox.py:50` and `packing/selector.py:31`
(both defensive branches — an empty containers list and a zero-cost box
divide guard) and 5 lines in `warehouse/models.py` (`__str__` methods,
exercised visually via the admin but not asserted on directly). Not
considered worth chasing to 100% — see `docs/DESIGN_DECISIONS.md` for the
general philosophy of not optimizing metrics past the point they're useful.

## Manual smoke test (dev server, real HTTP)

```
$ python manage.py runserver 8000 &
$ curl -s -o /dev/null -w "home: %{http_code}\n" http://127.0.0.1:8000/
home: 200
$ curl -s -o /dev/null -w "visualize: %{http_code}\n" http://127.0.0.1:8000/visualize/1/
visualize: 200
$ curl -s -o /dev/null -w "admin: %{http_code}\n" http://127.0.0.1:8000/admin/
admin: 302   (redirect to login — expected, unauthenticated)
$ curl -s -o /dev/null -w "docs: %{http_code}\n" http://127.0.0.1:8000/api/docs/
docs: 200
$ curl -s -o /dev/null -w "schema: %{http_code}\n" http://127.0.0.1:8000/api/schema/
schema: 200
```

`python manage.py recommend_box --order DEMO-001` output (verified real, see
`AI_USAGE.md` for the note on Windows console codepage rendering of the em
dash / m³ characters — cosmetic terminal-only issue, not a bug):

```
Order DEMO-001
  Strategy:    SINGLE_BOX
  Box:         M (Medium Carton)
  Cost:        40.00
  Utilization: 8%

Box         Verdict     Stage       Reason
------------------------------------------------------------------------------------------
FLAT        REJECTED    item_too_large  'Ceramic Mug' (110x90x95 mm) fits in no orientation inside box FLAT (350x250x30 mm)
L           FITS_BUT_COSTLIER  selection   Fits. Not selected — see recommended box.
M           SELECTED    selection   Cheapest box that fits everything (cost=40.00, utilization=8%)
S           REJECTED    geometry    All items individually fit, and total volume fits, but they can't be simultaneously arranged inside box S — no space left for: Paperback Novel
TUBE        REJECTED    item_too_large  'Ceramic Mug' (110x90x95 mm) fits in no orientation inside box TUBE (600x90x90 mm)
XL          FITS_BUT_COSTLIER  selection   Fits. Not selected — see recommended box.
XS          REJECTED    volume      Items total 1,451,340 mm³; box XS interior is only 1,200,000 mm³
```

## Docker

Not run locally — no Docker installation on this machine (see
`AI_USAGE.md`). `Dockerfile`/`docker-compose.yml` follow the standard
`python:3.12-slim` + `pip install` + `migrate && runserver` pattern and are
unmodified from a typical known-working shape, but this is flagged
honestly rather than claimed as verified.
