
ServiceApi.proto.RockwellAutomation.FactoryTalkLogixEcho.Api.V1"
IsConnectedArguments")
IsConnectedReturn
is_connected ("
SubscribeToUpdatesArguments"9
SubscribeToUpdatesReturn
message (
uuid (";
CreateChassisArguments
name (	
description (	"g
CreateChassisReturnP
chassis (2?.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ChassisDataItem"&
DeleteChassisArguments
uuid ("
DeleteChassisReturn"
ListChassisArguments"j
ListChassisReturnU
chassis_list (2?.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ChassisDataItem"¶
ChassisDataItem
uuid (
name (	
description (	`
slot_assignment_list (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SlotAssignmentItem
capacity ("[
SlotAssignmentItem
slot_number (
controller_uuid (
controller_name (	"$
ReadChassisArguments
uuid ("e
ReadChassisReturnP
chassis (2?.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ChassisDataItem"g
!ListAvailableSlotNumbersArguments
chassis_uuid (
controller_uuid (
has_partner (":
ListAvailableSlotNumbersReturn
slot_number_list ("j
UpdateChassisArgumentsP
chassis (2?.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ChassisDataItem"
UpdateChassisReturn"
LicenseInfoArguments"ê
PersonalizedLicenseDataItem
company_name (	
company_address (	
company_registered_user (	
company_phone (	
expiry_date (	
serial_number (	
product_info (	
product_name (	
text	 (	"Ï
LicenseInfoReturnQ
license_type (2;.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.LicenseType
is_license_valid ('
grace_period_duration_remaining (
is_personalized_license (n
personalized_license_info (2K.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.PersonalizedLicenseDataItem
description (	"‹
ProductInfoDataItem
short_copyright (	
long_copyright (	
product_name (	
product_version (	
support_link (	"
GetProductInfoArguments"q
GetProductInfoReturnY
product_info (2C.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ProductInfoDataItem"4
Ip4Configuration
address (
netmask ("}
CreateControllerArguments`
controller_data_item (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem"p
CreateControllerReturnV

controller (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem"5
!GetControllerInfoFromAcdArguments
acd_path (	"x
GetControllerInfoFromAcdReturnV

controller (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem"(
ListControllersArguments
uuid ("ˆ	
ControllerDataItem
firmware_package_uuid (
controller_uuid (
name (	
description (	
chassis_uuid (
chassis_name (	
slot (Z
ip_configuration (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.Ip4Configuration^
key_switch_position	 (2A.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.KeySwitchPosition

is_enabled
 (
is_sd_card_attached (
user_project_path (	
firmware_package_name (	a
firmware_package_version (2?.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.VersionDataItem
serial (]

error_code (2I.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerStatusErrorCode
is_in_run_mode (

is_faulted (
loaded_project_name (	L
mode (2>.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerModeh
continuous_task_fidelity (2F.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerTaskFidelity
	is_safety (
has_partner (
is_read_only (
has_chassis (
has_multiport (
is_dlr_mode (d
ip_configuration_secondary (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.Ip4Configuration"p
ListControllersReturnW
controllers (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem")
DeleteControllerArguments
uuid ("
DeleteControllerReturn"‡
ReplaceControllerArguments
controller_uuid (
firmware_uuid (
has_partner (
is_dlr_mode (
address ("q
ReplaceControllerReturnV

controller (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem"'
ReadControllerArguments
uuid ("n
ReadControllerReturnV

controller (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem"7
ListFirmwarePackagesArugments
supported_only ("w
ListFirmwarePackagesReturnY
packages (2G.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.FirmwarePackageDataItem"ž
FirmwarePackageDataItem
uuid (
name (	P
version (2?.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.VersionDataItem]
catalog_number (2E.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CatalogNumberDataItem
has_chassis (a
supported_products (2E.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CatalogNumberDataItem
	is_safety (
is_supported (
has_multiport	 ("A
VersionDataItem
major (
minor (
subminor ("Q
CatalogNumberDataItem
name (	
product_type (
product_code (",
ReadFirmwarePackageArguments
guid ("u
ReadFirmwarePackageReturnX
package (2G.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.FirmwarePackageDataItem")
'ListAvailableEthernetAddressesArguments"‚
$ListAvailableEthernetAddressesReturnZ
ethernet_list (2C.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.EthernetAddressItem" 
EthernetAddressItem

ip_address (
mac_address (
device_name (	
assigned_device_uuid (
netmask (
is_preferred_address ("-
ReadControllerBySnArguments
serial ("r
ReadControllerBySnReturnV

controller (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem"s
UpdateControllerArgumentsV

controller (2B.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerDataItem"
UpdateControllerReturn"o
'ListFirmwarePackagesWithParamsArguments
major_revision (
product_code (
supported_only ("
$ListFirmwarePackagesWithParamsReturnY
packages (2G.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.FirmwarePackageDataItem"/
InstallFirmwarePackageArguments
path (	"x
InstallFirmwarePackageReturnX
package (2G.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.FirmwarePackageDataItem"}
!UninstallFirmwarePackageArgumentsX
package (2G.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.FirmwarePackageDataItem" 
UninstallFirmwarePackageReturn"P
DownloadArguments
controller_uuid (
session_uuid (
path (	"
DownloadReturn"1
AbortDownloadArguments
controller_uuid ("2
CancelDownloadArguments
controller_uuid ("
AbortDownloadReturn"
CancelDownloadReturn"M
GetDownloadFeedbackArguments
controller_uuid (
session_uuid ("w
GetDownloadFeedbackReturnZ
feedback (2H.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DownloadFeedbackDataItem"ë
DownloadFeedbackDataItem
controller_name (	
controller_uuid (
chassis_name (	
chassis_uuid (M
state (2>.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.OperationState
progress (
messages (	":
"GetAllDownloadsInProgressArguments
session_uuid ("}
GetAllDownloadsInProgressReturnZ
feedback (2H.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DownloadFeedbackDataItem"I
 SetVirtualBackplaneSlotArguments
controller_uuid (
slot ("
SetVirtualBackplaneSlotReturn"?
$GetControllerConnectionInfoArguments
controller_uuid ("=
!GetControllerConnectionInfoReturn

ip (
port ("Ò
ControllerSnapshotDataItem
firmware_package_uuid (
serial_number (
name (	
description (	
chassis_uuid (
chassis_name (	
slot (Z
ip_configuration (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.Ip4Configuration^
key_switch_position	 (2A.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.KeySwitchPosition
is_sd_card_attached (
user_project_path (	
firmware_package_name (	a
firmware_package_version (2?.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.VersionDataItem
has_partner (
chassis_description (	d
ip_configuration_secondary (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.Ip4Configuration
is_dlr_mode ("‘
SnapshotInconsistencyDataItem_
severity (2M.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotInconsistencySeverity
message (	"ª
SnapshotDataItem
snapshot_uuid (
name (	
description (	
timestamp_s (_
controllers (2J.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ControllerSnapshotDataItemf
inconsistencies (2M.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotInconsistencyDataItem"
ListSnapshotsArguments"n
ListSnapshotsReturnW
snapshot_list (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotDataItem".
ReadSnapshotArguments
snapshot_uuid ("h
ReadSnapshotReturnR
snapshot (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotDataItem"V
CreateSnapshotArguments
controller_uuids (
name (	
description (	"j
CreateSnapshotReturnR
snapshot (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotDataItem"¦
RestoreSnapshotArguments
snapshot_uuid (
session_uuid (]
restore_option (2E.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.RestoreSnapshotOption"
RestoreSnapshotReturn"6
AbortSnapshotRestoreArguments
snapshot_uuid ("7
CancelSnapshotRestoreArguments
snapshot_uuid ("
AbortSnapshotRestoreReturn"
CancelSnapshotRestoreReturn"S
UpdateSnapshotArguments
snapshot_uuid (
name (	
description (	"j
UpdateSnapshotReturnR
snapshot (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotDataItem"0
DeleteSnapshotArguments
snapshot_uuid ("
DeleteSnapshotReturn"'
ImportSnapshotArguments
path (	"j
ImportSnapshotReturnR
snapshot (2@.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotDataItem">
ExportSnapshotArguments
snapshot_uuid (
path (	"
ExportSnapshotReturn"«
SnapshotRestoreFeedbackDataItem
snapshot_uuid (
progress (M
state (2>.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.OperationState
messages (	"R
#GetSnapshotRestoreFeedbackArguments
snapshot_uuid (
session_uuid ("…
 GetSnapshotRestoreFeedbackReturna
feedback (2O.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SnapshotRestoreFeedbackDataItem"#
!GetDownloadDirectoryPathArguments".
GetDownloadDirectoryPathReturn
path (	"1
GetSdCardPathArguments
controller_uuid ("#
GetSdCardPathReturn
path (	"#
!IsLogixDesignerInstalledArguments"3
IsLogixDesignerInstalledReturn
	installed ("*
(GetLocalSharedStorageParametersArguments"G
%GetLocalSharedStorageParametersReturn
path (	
username (	"
GetDataCollectorPathArguments"*
GetDataCollectorPathReturn
path (	*R
LicenseType
NONE 
PERSONALIZED
STANDARD	
GRACE

NOT_IN_USE*5
KeySwitchPosition
RUN 

REMOTE
PROGRAM*e
ControllerMode
HARD_RUN 

REMOTE_RUN
REMOTE_PROGRAM
REMOTE_TEST
HARD_PROGRAM*s
ControllerStatusErrorCode
CONTROLLER_STATUS_OK 
CREATION_ERROR
CLOSED_EXTERNALLY
REMOVAL_ERROR*:
ControllerTaskFidelity

RUN_OK 
RUN_LOW_FIDELITY*c
OperationState
DONE 

FAILED
IN_PROGRESS
CANCELED
NO_OPERATION_IN_PROGRESS* 
MetaDataKey
UNSPECIFIED 
LANGUAGE
	CLIENT_ID
CLIENT_DESCRIPTIVE_NAME
CLIENT_USERNAME
CLIENT_FULL_NAME
FACTORY_TALK_USER_TOKEN*m
RestoreSnapshotOption
REPLACE_ONLY 
CREATE_ONLY
REPLACE_AND_CREATE
DELETE_ALL_AND_CREATE*A
SnapshotInconsistencySeverity
INFO 
WARNING	
ERROR2É@

ServiceApi˜
IsConnectedD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.IsConnectedArgumentsA.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.IsConnectedReturn" ¯
SubscribeToUpdatesK.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SubscribeToUpdatesArgumentsH.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SubscribeToUpdatesReturn" 0ž
CreateChassisF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CreateChassisArgumentsC.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CreateChassisReturn" ž
DeleteChassisF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DeleteChassisArgumentsC.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DeleteChassisReturn" ˜
ListChassisD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListChassisArgumentsA.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListChassisReturn" ˜
ReadChassisD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadChassisArgumentsA.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadChassisReturn" ž
UpdateChassisF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UpdateChassisArgumentsC.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UpdateChassisReturn" ¿
ListAvailableSlotNumbersQ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListAvailableSlotNumbersArgumentsN.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListAvailableSlotNumbersReturn" ›
GetLicenseInfoD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.LicenseInfoArgumentsA.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.LicenseInfoReturn" ¡
GetProductInfoG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetProductInfoArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetProductInfoReturn" §
CreateControllerI.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CreateControllerArgumentsF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CreateControllerReturn" ¿
GetControllerInfoFromAcdQ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetControllerInfoFromAcdArgumentsN.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetControllerInfoFromAcdReturn" ¤
ListControllersH.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListControllersArgumentsE.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListControllersReturn" §
DeleteControllerI.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DeleteControllerArgumentsF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DeleteControllerReturn" ª
ReplaceControllerJ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReplaceControllerArgumentsG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReplaceControllerReturn" ¡
ReadControllerG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadControllerArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadControllerReturn" ³
ListFirmwarePackagesM.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListFirmwarePackagesArugmentsJ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListFirmwarePackagesReturn" Ñ
ListAvailableEthernetAddressesW.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListAvailableEthernetAddressesArgumentsT.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListAvailableEthernetAddressesReturn" °
ReadFirmwarePackageL.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadFirmwarePackageArgumentsI.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadFirmwarePackageReturn" ­
ReadControllerBySnK.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadControllerBySnArgumentsH.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadControllerBySnReturn" §
UpdateControllerI.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UpdateControllerArgumentsF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UpdateControllerReturn" Ñ
ListFirmwarePackagesWithParamsW.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListFirmwarePackagesWithParamsArgumentsT.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListFirmwarePackagesWithParamsReturn" ¹
InstallFirmwarePackageO.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.InstallFirmwarePackageArgumentsL.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.InstallFirmwarePackageReturn" ¿
UninstallFirmwarePackageQ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UninstallFirmwarePackageArgumentsN.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UninstallFirmwarePackageReturn" 
DownloadA.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DownloadArguments>.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DownloadReturn" ž
AbortDownloadF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.AbortDownloadArgumentsC.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.AbortDownloadReturn" ¡
CancelDownloadG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CancelDownloadArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CancelDownloadReturn" °
GetDownloadFeedbackL.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetDownloadFeedbackArgumentsI.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetDownloadFeedbackReturn" Â
GetAllDownloadsInProgressR.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetAllDownloadsInProgressArgumentsO.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetAllDownloadsInProgressReturn" ¼
SetVirtualBackplaneSlotP.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SetVirtualBackplaneSlotArgumentsM.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.SetVirtualBackplaneSlotReturn" È
GetControllerConnectionInfoT.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetControllerConnectionInfoArgumentsQ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetControllerConnectionInfoReturn" ž
ListSnapshotsF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListSnapshotsArgumentsC.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ListSnapshotsReturn" ›
ReadSnapshotE.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadSnapshotArgumentsB.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ReadSnapshotReturn" ¡
CreateSnapshotG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CreateSnapshotArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CreateSnapshotReturn" ¤
RestoreSnapshotH.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.RestoreSnapshotArgumentsE.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.RestoreSnapshotReturn" ³
AbortSnapshotRestoreM.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.AbortSnapshotRestoreArgumentsJ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.AbortSnapshotRestoreReturn" ¶
CancelSnapshotRestoreN.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CancelSnapshotRestoreArgumentsK.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.CancelSnapshotRestoreReturn" ¡
UpdateSnapshotG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UpdateSnapshotArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.UpdateSnapshotReturn" ¡
DeleteSnapshotG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DeleteSnapshotArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.DeleteSnapshotReturn" ¡
ImportSnapshotG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ImportSnapshotArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ImportSnapshotReturn" ¡
ExportSnapshotG.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ExportSnapshotArgumentsD.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.ExportSnapshotReturn" Å
GetSnapshotRestoreFeedbackS.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetSnapshotRestoreFeedbackArgumentsP.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetSnapshotRestoreFeedbackReturn" ¿
GetDownloadDirectoryPathQ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetDownloadDirectoryPathArgumentsN.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetDownloadDirectoryPathReturn" ž
GetSdCardPathF.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetSdCardPathArgumentsC.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetSdCardPathReturn" ¿
IsLogixDesignerInstalledQ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.IsLogixDesignerInstalledArgumentsN.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.IsLogixDesignerInstalledReturn" Ô
GetLocalSharedStorageParametersX.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetLocalSharedStorageParametersArgumentsU.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetLocalSharedStorageParametersReturn" ³
GetDataCollectorPathM.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetDataCollectorPathArgumentsJ.RockwellAutomation.FactoryTalkLogixEcho.Api.V1.GetDataCollectorPathReturn" bproto3