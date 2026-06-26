output "network_anchors" {
  description = "Network Anchor details keyed by the network_anchors map key."
  value = { for k, v in azapi_resource.network_anchor : k => {
    id   = v.id
    name = v.name
  } }
}
