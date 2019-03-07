# Changelog

## Version 1.4.0 (March, 2019)

* Added ...
    * introdotta il campo provider nella classe common.model.authorization.User per indicare l'autentication provider
    * aggiunta la gestione del campo provider nelle api di auth.user
* Fixed ...
    * revisione del metodo user_request
    * modificata l'api di interrogazione dei domains in interrogazione dei providers
    * modificata la configurazione di un authentication provider ldap
    * aggiornamento firma metodo get_entity: inserimento params *args, **kvargs
* Integrated ...
* Various bugfixes

## Version 1.3.0 (February 27, 2019)

* Added ...
    * aggiunto runner per realizzare test unit concorrenti
* Fixed ...
    * aumenteta la dimensione del campo desc della tabella event a 500 caratteri
* Integrated ...
* Various bugfixes

## Version 1.2.0 (February 01, 2019)

* Added ...
    * **BeehiveApiClient** aggiunto metodo set_ssh_group_authorization
* Fixed ...
    * corretto bug nella classe PaginatedQueryGenerator che impediva il cambio del campo di group by
* Integrated ...
* Various bugfixes

## Version 1.1.0 (January 13, 2019)

* Added ...
    * aggiunti il riferimento dei jobs invocati nel task chiamanate
* Fixed ...
    * trace: cambiato il tracciato degli eventi. Viene stampato il nome del metodo tracciato
    * event: revisione della query di lista. Era troppo lenta. Limitata la query a un giorno.
    * auth: rivisto metodo per verificare che uno user abbia un certo ruolo
* Integrated ...
* Various bugfixes

## Version 1.0.0 (July 31, 2018)

First production preview release.

## Version 0.1.0 (April 18, 2016)

First private preview release.